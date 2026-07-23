from __future__ import annotations

import cv2
import numpy as np
import pytest

from app.detection.door_detector import (
    MIN_DOOR_W,
    DoorDetector,
)
from app.detection.schemas import (
    Door,
    DoorType,
    LineCategory,
    LineSegment,
)


@pytest.fixture
def detector() -> DoorDetector:
    return DoorDetector()


def _make_blank_image(h: int = 400, w: int = 400) -> np.ndarray:
    return np.full((h, w, 3), 255, dtype=np.uint8)


def _make_wall_with_gap(
    h: int = 400, w: int = 400,
    wall_y: int = 200, gap_x1: int = 150, gap_x2: int = 220,
) -> np.ndarray:
    img = np.full((h, w, 3), 255, dtype=np.uint8)
    cv2.line(img, (0, wall_y), (w - 1, wall_y), (0, 0, 0), 3)
    cv2.rectangle(img, (gap_x1, wall_y - 2), (gap_x2, wall_y + 2), (255, 255, 255), -1)
    return img


def _make_binary_wall_with_gap(
    h: int = 400, w: int = 400,
    wall_y: int = 200, gap_x1: int = 150, gap_x2: int = 220,
) -> np.ndarray:
    binary = np.full((h, w), 255, dtype=np.uint8)
    binary[wall_y, 0:gap_x1] = 0
    binary[wall_y, gap_x2:w] = 0
    return binary


class TestDetectBlankImage:
    def test_returns_empty_doors(self, detector: DoorDetector):
        img = _make_blank_image()
        binary = np.full((400, 400), 255, dtype=np.uint8)
        result = detector.detect(img, grouped_lines=[], all_lines=[], binary=binary)
        assert len(result.doors) == 0
        assert result.image_width == 400
        assert result.image_height == 400


class TestComputeThreshold:
    def test_uniform_image(self):
        gray = np.full((100, 100), 128, dtype=np.uint8)
        t = DoorDetector._compute_threshold(gray)
        assert t == 128.0

    def test_high_contrast(self):
        gray = np.zeros((100, 100), dtype=np.uint8)
        gray[:50, :] = 255
        t = DoorDetector._compute_threshold(gray)
        assert 80.0 <= t <= 180.0

    def test_low_contrast(self):
        gray = np.full((100, 100), 120, dtype=np.uint8)
        gray[40:60, 40:60] = 140
        t = DoorDetector._compute_threshold(gray)
        assert t >= 80.0


class TestIsWallEdge:
    def test_identifies_wall_edge_vertical(self, detector: DoorDetector):
        gray = np.full((400, 400), 255, dtype=np.uint8)
        gray[:, 198] = 0
        gray[:, 202] = 0
        line = LineSegment(
            x1=200.0, y1=50.0, x2=200.0, y2=350.0,
            angle=90.0, length=300.0, category=LineCategory.VERTICAL,
        )
        assert detector._is_wall_edge(line, gray, 128.0) is True

    def test_identifies_non_wall_line(self, detector: DoorDetector):
        gray = np.full((400, 400), 255, dtype=np.uint8)
        line = LineSegment(
            x1=200.0, y1=195.0, x2=200.0, y2=205.0,
            angle=90.0, length=10.0, category=LineCategory.VERTICAL,
        )
        assert detector._is_wall_edge(line, gray, 128.0) is False

    def test_identifies_wall_edge_horizontal(self, detector: DoorDetector):
        gray = np.full((400, 400), 255, dtype=np.uint8)
        gray[198, :] = 0
        gray[202, :] = 0
        line = LineSegment(
            x1=50.0, y1=200.0, x2=350.0, y2=200.0,
            angle=0.0, length=300.0, category=LineCategory.HORIZONTAL,
        )
        assert detector._is_wall_edge(line, gray, 128.0) is True

    def test_diagonal_not_wall_edge(self, detector: DoorDetector):
        gray = np.full((400, 400), 255, dtype=np.uint8)
        line = LineSegment(
            x1=50.0, y1=50.0, x2=350.0, y2=350.0,
            angle=45.0, length=424.3, category=LineCategory.DIAGONAL,
        )
        assert detector._is_wall_edge(line, gray, 128.0) is False


class TestFindGapOnLine:
    def test_finds_gap_in_horizontal_wall(self, detector: DoorDetector):
        gray = np.full((400, 400), 255, dtype=np.uint8)
        gray[200, 0:100] = 0
        gray[200, 160:400] = 0
        gs, ge = DoorDetector._find_gap_on_line(
            gray, fixed_coord=200, scan_start=0, scan_end=399,
            hinge_pos=120, is_horizontal=True, threshold=128.0,
        )
        assert gs is not None
        assert ge is not None
        assert ge - gs >= MIN_DOOR_W

    def test_no_gap_returns_none(self, detector: DoorDetector):
        gray = np.full((400, 400), 128, dtype=np.uint8)
        gs, ge = DoorDetector._find_gap_on_line(
            gray, fixed_coord=200, scan_start=100, scan_end=300,
            hinge_pos=200, is_horizontal=True, threshold=128.0,
        )
        assert gs is None
        assert ge is None

    def test_finds_gap_in_vertical_wall(self, detector: DoorDetector):
        gray = np.full((400, 400), 255, dtype=np.uint8)
        gray[0:100, 200] = 0
        gray[160:400, 200] = 0
        gs, ge = DoorDetector._find_gap_on_line(
            gray, fixed_coord=200, scan_start=0, scan_end=399,
            hinge_pos=120, is_horizontal=False, threshold=128.0,
        )
        assert gs is not None
        assert ge is not None


class TestDeduplicateDoors:
    def test_merges_overlapping_doors(self, detector: DoorDetector):
        d1 = Door(
            type=DoorType.SINGLE, x=100, y=200, width=70, rotation=0,
            hinge_x=150, hinge_y=200, leaf_length=50,
            leaf_x1=100, leaf_y1=200, leaf_x2=150, leaf_y2=200,
            wall_gap_x1=100, wall_gap_y1=198, wall_gap_x2=170, wall_gap_y2=202,
            swing="right", confidence=0.6,
        )
        d2 = Door(
            type=DoorType.SINGLE, x=105, y=200, width=70, rotation=0,
            hinge_x=152, hinge_y=200, leaf_length=50,
            leaf_x1=100, leaf_y1=200, leaf_x2=152, leaf_y2=200,
            wall_gap_x1=100, wall_gap_y1=198, wall_gap_x2=170, wall_gap_y2=202,
            swing="right", confidence=0.7,
        )
        result = DoorDetector._deduplicate_doors([d1, d2])
        assert len(result) == 1

    def test_keeps_different_doors(self, detector: DoorDetector):
        d1 = Door(
            type=DoorType.SINGLE, x=100, y=100, width=70, rotation=0,
            hinge_x=150, hinge_y=100, leaf_length=50,
            wall_gap_x1=100, wall_gap_y1=98, wall_gap_x2=170, wall_gap_y2=102,
            swing="right", confidence=0.6,
        )
        d2 = Door(
            type=DoorType.SINGLE, x=300, y=300, width=70, rotation=0,
            hinge_x=350, hinge_y=300, leaf_length=50,
            wall_gap_x1=300, wall_gap_y1=298, wall_gap_x2=370, wall_gap_y2=302,
            swing="right", confidence=0.6,
        )
        result = DoorDetector._deduplicate_doors([d1, d2])
        assert len(result) == 2

    def test_single_door_unchanged(self, detector: DoorDetector):
        d = Door(
            type=DoorType.SINGLE, x=100, y=200, width=70, rotation=0,
            hinge_x=150, hinge_y=200, leaf_length=50,
            wall_gap_x1=100, wall_gap_y1=198, wall_gap_x2=170, wall_gap_y2=202,
            swing="right", confidence=0.6,
        )
        result = DoorDetector._deduplicate_doors([d])
        assert len(result) == 1


class TestClassifyDoubleDoors:
    def test_pairs_nearby_doors(self, detector: DoorDetector):
        d1 = Door(
            type=DoorType.SINGLE, x=100, y=200, width=35, rotation=0,
            hinge_x=120, hinge_y=200, leaf_length=30,
            wall_gap_x1=100, wall_gap_y1=198, wall_gap_x2=135, wall_gap_y2=202,
            swing="right", confidence=0.6,
        )
        d2 = Door(
            type=DoorType.SINGLE, x=140, y=200, width=35, rotation=0,
            hinge_x=155, hinge_y=200, leaf_length=30,
            wall_gap_x1=100, wall_gap_y1=198, wall_gap_x2=140, wall_gap_y2=202,
            swing="left", confidence=0.6,
        )
        result = DoorDetector._classify_double_doors([d1, d2])
        doubles = [d for d in result if d.type == DoorType.DOUBLE]
        assert len(doubles) == 1

    def test_keeps_single_when_far_apart(self, detector: DoorDetector):
        d1 = Door(
            type=DoorType.SINGLE, x=50, y=100, width=35, rotation=0,
            hinge_x=60, hinge_y=100, leaf_length=30,
            wall_gap_x1=50, wall_gap_y1=98, wall_gap_x2=85, wall_gap_y2=102,
            swing="right", confidence=0.6,
        )
        d2 = Door(
            type=DoorType.SINGLE, x=300, y=100, width=35, rotation=0,
            hinge_x=310, hinge_y=100, leaf_length=30,
            wall_gap_x1=300, wall_gap_y1=98, wall_gap_x2=335, wall_gap_y2=102,
            swing="left", confidence=0.6,
        )
        result = DoorDetector._classify_double_doors([d1, d2])
        assert len(result) == 2
        assert all(d.type == DoorType.SINGLE for d in result)


class TestClassifySlidingDoors:
    def test_detects_parallel_tracks(self, detector: DoorDetector):
        gray = np.full((400, 400), 255, dtype=np.uint8)
        gray[200, 160:170] = 0
        gray[200, 190:200] = 0
        door = Door(
            type=DoorType.SINGLE, x=200, y=200, width=100, rotation=0,
            hinge_x=150, hinge_y=200, leaf_length=50,
            wall_gap_x1=150, wall_gap_y1=198, wall_gap_x2=250, wall_gap_y2=202,
            swing="right", confidence=0.6,
        )
        result = detector._classify_sliding_doors([door], gray)
        sliding = [d for d in result if d.type == DoorType.SLIDING]
        assert len(sliding) == 1

    def test_preserves_non_sliding(self, detector: DoorDetector):
        gray = np.full((400, 400), 255, dtype=np.uint8)
        door = Door(
            type=DoorType.DOUBLE, x=200, y=200, width=100, rotation=0,
            hinge_x=150, hinge_y=200, leaf_length=50,
            swing="both", confidence=0.7,
        )
        result = detector._classify_sliding_doors([door], gray)
        assert len(result) == 1
        assert result[0].type == DoorType.DOUBLE


class TestHasParallelTracks:
    def test_horizontal_with_tracks(self, detector: DoorDetector):
        gray = np.full((400, 400), 255, dtype=np.uint8)
        gray[200, 120:130] = 0
        gray[200, 160:170] = 0
        door = Door(
            type=DoorType.SINGLE, x=150, y=200, width=100, rotation=0,
            hinge_x=100, hinge_y=200, leaf_length=50,
            wall_gap_x1=100, wall_gap_y1=198, wall_gap_x2=200, wall_gap_y2=202,
            swing="right", confidence=0.6,
        )
        assert DoorDetector._has_parallel_tracks(door, gray, 128.0) is True

    def test_vertical_with_tracks(self, detector: DoorDetector):
        gray = np.full((400, 400), 255, dtype=np.uint8)
        gray[120:130, 200] = 0
        gray[160:170, 200] = 0
        door = Door(
            type=DoorType.SINGLE, x=200, y=150, width=100, rotation=90,
            hinge_x=200, hinge_y=100, leaf_length=50,
            wall_gap_x1=198, wall_gap_y1=100, wall_gap_x2=202, wall_gap_y2=200,
            swing="down", confidence=0.6,
        )
        assert DoorDetector._has_parallel_tracks(door, gray, 128.0) is True

    def test_no_tracks(self, detector: DoorDetector):
        gray = np.full((400, 400), 255, dtype=np.uint8)
        door = Door(
            type=DoorType.SINGLE, x=150, y=200, width=100, rotation=0,
            hinge_x=100, hinge_y=200, leaf_length=50,
            wall_gap_x1=100, wall_gap_y1=198, wall_gap_x2=200, wall_gap_y2=202,
            swing="right", confidence=0.6,
        )
        assert DoorDetector._has_parallel_tracks(door, gray, 128.0) is False
