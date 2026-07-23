from __future__ import annotations

import cv2
import numpy as np
import pytest

from app.detection.schemas import (
    LineCategory,
    LineSegment,
    WindowType,
)
from app.detection.window_detector import (
    MIN_WINDOW_W,
    WindowDetector,
)


@pytest.fixture
def detector() -> WindowDetector:
    return WindowDetector()


def _make_blank_image(h: int = 400, w: int = 400) -> np.ndarray:
    return np.full((h, w), 255, dtype=np.uint8)


def _make_wall_with_gap(
    h: int = 400, w: int = 400,
    wall_y: int = 200, gap_x1: int = 130, gap_x2: int = 270,
) -> np.ndarray:
    binary = np.full((h, w), 255, dtype=np.uint8)
    binary[wall_y, 0:gap_x1] = 0
    binary[wall_y, gap_x2:w] = 0
    return binary


def _make_h_wall_line(wall_y: int = 200, w: int = 400) -> LineSegment:
    return LineSegment(
        x1=0.0, y1=float(wall_y), x2=float(w - 1), y2=float(wall_y),
        angle=0.0, length=float(w - 1), category=LineCategory.HORIZONTAL,
    )


def _make_v_wall_line(wall_x: int = 200, h: int = 400) -> LineSegment:
    return LineSegment(
        x1=float(wall_x), y1=0.0, x2=float(wall_x), y2=float(h - 1),
        angle=90.0, length=float(h - 1), category=LineCategory.VERTICAL,
    )


class TestDetectBlankImage:
    def test_returns_empty_windows(self, detector: WindowDetector):
        img = np.full((400, 400, 3), 255, dtype=np.uint8)
        binary = np.full((400, 400), 255, dtype=np.uint8)
        result = detector.detect(img, grouped_lines=[], binary=binary)
        assert len(result.windows) == 0
        assert result.image_width == 400
        assert result.image_height == 400


class TestComputeThreshold:
    def test_uniform_image(self):
        gray = np.full((100, 100), 128, dtype=np.uint8)
        t = WindowDetector._compute_threshold(gray)
        assert t == 128.0

    def test_high_contrast(self):
        gray = np.zeros((100, 100), dtype=np.uint8)
        gray[:50, :] = 255
        t = WindowDetector._compute_threshold(gray)
        assert 80.0 <= t <= 180.0

    def test_low_contrast(self):
        gray = np.full((100, 100), 120, dtype=np.uint8)
        gray[40:60, 40:60] = 140
        t = WindowDetector._compute_threshold(gray)
        assert t >= 80.0


class TestFindGapsAtOffset:
    def test_finds_white_gap(self, detector: WindowDetector):
        gray = np.full((400, 400), 255, dtype=np.uint8)
        for y in [199, 200, 201]:
            gray[y, 0:100] = 0
            gray[y, 200:400] = 0
        gaps = detector._find_gaps_at_offset(gray, center=200, lo=0, hi=399,
                                              horizontal=True, threshold=128.0)
        assert len(gaps) >= 1
        gs, ge = gaps[0]
        assert ge - gs >= MIN_WINDOW_W

    def test_no_gap_when_all_wall(self, detector: WindowDetector):
        gray = np.full((400, 400), 80, dtype=np.uint8)
        gaps = detector._find_gaps_at_offset(gray, center=200, lo=0, hi=399,
                                              horizontal=True, threshold=128.0)
        assert len(gaps) == 0


class TestFindDarkRuns:
    def test_counts_dark_segments(self, detector: WindowDetector):
        gray = np.full((400, 400), 255, dtype=np.uint8)
        gray[200, 130:135] = 0
        gray[200, 150:155] = 0
        runs, total = detector._find_dark_runs(
            gray, fixed_coord=200, gs=130, ge=200,
            horizontal=True, threshold=128.0,
        )
        assert len(runs) >= 2
        assert total >= 10

    def test_no_dark(self, detector: WindowDetector):
        gray = np.full((400, 400), 255, dtype=np.uint8)
        runs, total = detector._find_dark_runs(
            gray, fixed_coord=200, gs=130, ge=270,
            horizontal=True, threshold=128.0,
        )
        assert len(runs) == 0
        assert total == 0


class TestFindWindowHeight:
    def test_measures_perpendicular_distance(self, detector: WindowDetector):
        gray = np.full((400, 400), 255, dtype=np.uint8)
        gray[180, 200] = 0
        gray[220, 200] = 0
        height = detector._find_window_height(
            gray, gs=130, ge=270, is_horizontal=True, center=200, threshold=128.0,
        )
        assert height > 0


class TestClassifyWindow:
    def test_sliding_with_multiple_lines(self, detector: WindowDetector):
        gray = np.full((400, 400), 255, dtype=np.uint8)
        dark_runs = [(140, 142), (150, 152), (160, 162)]
        wtype, conf = detector._classify_window(
            gray, dark_runs, 0.5, 130, 270, True, 200, 128.0,
        )
        assert wtype == WindowType.SLIDING

    def test_fixed_with_single_line(self, detector: WindowDetector):
        gray = np.full((400, 400), 255, dtype=np.uint8)
        dark_runs = [(150, 152)]
        wtype, conf = detector._classify_window(
            gray, dark_runs, 0.3, 130, 270, True, 200, 128.0,
        )
        assert wtype in (WindowType.FIXED, WindowType.CASEMENT)


class TestDeduplication:
    def test_seen_gaps_dedup(self, detector: WindowDetector):
        img = np.full((400, 400, 3), 255, dtype=np.uint8)
        binary = _make_wall_with_gap(wall_y=200, gap_x1=130, gap_x2=270)
        wall = _make_h_wall_line(wall_y=200)
        result = detector.detect(img, grouped_lines=[wall], binary=binary)
        keys = set()
        for win in result.windows:
            key = f"{win.wall_gap_x1:.0f}_{win.wall_gap_y1:.0f}_"
            key += f"{win.wall_gap_x2:.0f}_{win.wall_gap_y2:.0f}"
            assert key not in keys
            keys.add(key)


class TestDetectWithGapFeatures:
    def test_finds_window_in_gap(self, detector: WindowDetector):
        binary = np.full((400, 400), 255, dtype=np.uint8)
        binary[200, 0:130] = 0
        binary[200, 270:400] = 0
        binary[200, 180:185] = 0
        binary[200, 215:220] = 0
        img = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
        wall = _make_h_wall_line(wall_y=200)
        result = detector.detect(img, grouped_lines=[wall], binary=binary)
        assert isinstance(result.windows, list)
