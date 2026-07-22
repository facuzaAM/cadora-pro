from __future__ import annotations

import math

import numpy as np
import cv2
import pytest

from app.detection.line_detector import (
    LineDetector,
    RawLine,
    MIN_LINE_LENGTH,
    GROUP_DISTANCE_THRESHOLD,
    ANGLE_TOLERANCE,
)
from app.detection.schemas import LineCategory, LineSegment, Intersection


@pytest.fixture
def detector() -> LineDetector:
    return LineDetector()


def _make_blank_image(h: int = 400, w: int = 400) -> np.ndarray:
    return np.full((h, w, 3), 255, dtype=np.uint8)


def _draw_h_line(img: np.ndarray, y: int, x1: int, x2: int, thickness: int = 2) -> np.ndarray:
    cv2.line(img, (x1, y), (x2, y), (0, 0, 0), thickness)
    return img


def _draw_v_line(img: np.ndarray, x: int, y1: int, y2: int, thickness: int = 2) -> np.ndarray:
    cv2.line(img, (x, y1), (x, y2), (0, 0, 0), thickness)
    return img


def _make_binary_with_h_line(y: int, x1: int, x2: int, h: int = 400, w: int = 400) -> np.ndarray:
    binary = np.full((h, w), 255, dtype=np.uint8)
    binary[y, x1:x2] = 0
    return binary


def _make_binary_with_v_line(x: int, y1: int, y2: int, h: int = 400, w: int = 400) -> np.ndarray:
    binary = np.full((h, w), 255, dtype=np.uint8)
    binary[y1:y2, x] = 0
    return binary


class TestDetectBlankImage:
    def test_returns_empty_results(self, detector: LineDetector):
        img = _make_blank_image()
        binary = np.full((400, 400), 255, dtype=np.uint8)
        classified, grouped, intersections, w, h = detector.detect(img, binary=binary)
        assert isinstance(classified, list)
        assert isinstance(grouped, list)
        assert isinstance(intersections, list)
        assert w == 400
        assert h == 400


class TestDetectHorizontalLine:
    def test_finds_horizontal_line(self, detector: LineDetector):
        img = _make_blank_image()
        _draw_h_line(img, 200, 50, 350)
        binary = _make_binary_with_h_line(200, 50, 350)
        classified, grouped, _, _, _ = detector.detect(img, binary=binary)
        h_lines = [l for l in classified if l.category == LineCategory.HORIZONTAL]
        assert len(h_lines) >= 1


class TestDetectVerticalLine:
    def test_finds_vertical_line(self, detector: LineDetector):
        img = _make_blank_image()
        _draw_v_line(img, 200, 50, 350)
        binary = _make_binary_with_v_line(200, 50, 350)
        classified, grouped, _, _, _ = detector.detect(img, binary=binary)
        v_lines = [l for l in classified if l.category == LineCategory.VERTICAL]
        assert len(v_lines) >= 1


class TestDetectBothLines:
    def test_classifies_correctly(self, detector: LineDetector):
        img = _make_blank_image()
        _draw_h_line(img, 100, 30, 370)
        _draw_v_line(img, 200, 30, 370)
        binary = np.full((400, 400), 255, dtype=np.uint8)
        binary[100, 30:370] = 0
        binary[30:370, 200] = 0
        classified, grouped, _, _, _ = detector.detect(img, binary=binary)
        h_lines = [l for l in classified if l.category == LineCategory.HORIZONTAL]
        v_lines = [l for l in classified if l.category == LineCategory.VERTICAL]
        assert len(h_lines) >= 1
        assert len(v_lines) >= 1


class TestFilterNoise:
    def test_removes_short_lines(self, detector: LineDetector):
        short = RawLine(0, 0, 5, 0)
        long_line = RawLine(0, 0, 50, 0)
        result = detector._filter_noise([short, long_line])
        lengths = [LineDetector._line_length(l) for l in result]
        assert all(l >= MIN_LINE_LENGTH for l in lengths)

    def test_keeps_valid_lines(self, detector: LineDetector):
        lines = [RawLine(0, 0, 100, 0), RawLine(0, 0, 0, 100)]
        result = detector._filter_noise(lines)
        assert len(result) == 2

    def test_empty_list(self, detector: LineDetector):
        assert detector._filter_noise([]) == []


class TestGroupCollinear:
    def test_merges_nearby_collinear_segments(self, detector: LineDetector):
        lines = [
            LineSegment(id=__import__("uuid").uuid4(), x1=0, y1=100, x2=50, y2=100,
                        angle=0.0, length=50.0, category=LineCategory.HORIZONTAL),
            LineSegment(id=__import__("uuid").uuid4(), x1=60, y1=100, x2=120, y2=100,
                        angle=0.0, length=60.0, category=LineCategory.HORIZONTAL),
        ]
        result = detector._group_collinear(lines)
        h_merged = [l for l in result if l.category == LineCategory.HORIZONTAL]
        assert len(h_merged) == 1
        assert h_merged[0].x1 <= 0
        assert h_merged[0].x2 >= 120

    def test_empty_input(self, detector: LineDetector):
        assert detector._group_collinear([]) == []

    def test_single_line_unchanged(self, detector: LineDetector):
        lines = [
            LineSegment(id=__import__("uuid").uuid4(), x1=0, y1=50, x2=100, y2=50,
                        angle=0.0, length=100.0, category=LineCategory.HORIZONTAL),
        ]
        result = detector._group_collinear(lines)
        assert len(result) == 1


class TestFindIntersections:
    def test_finds_crossing_lines(self, detector: LineDetector):
        h = LineSegment(id=__import__("uuid").uuid4(), x1=0, y1=200, x2=400, y2=200,
                        angle=0.0, length=400.0, category=LineCategory.HORIZONTAL)
        v = LineSegment(id=__import__("uuid").uuid4(), x1=200, y1=0, x2=200, y2=400,
                        angle=90.0, length=400.0, category=LineCategory.VERTICAL)
        result = detector._find_intersections([h, v], (400, 400))
        assert len(result) >= 1
        ix = result[0].x
        iy = result[0].y
        assert abs(ix - 200) < 10
        assert abs(iy - 200) < 10

    def test_parallel_no_intersection(self, detector: LineDetector):
        a = LineSegment(id=__import__("uuid").uuid4(), x1=0, y1=100, x2=300, y2=100,
                        angle=0.0, length=300.0, category=LineCategory.HORIZONTAL)
        b = LineSegment(id=__import__("uuid").uuid4(), x1=0, y1=200, x2=300, y2=200,
                        angle=0.0, length=300.0, category=LineCategory.HORIZONTAL)
        result = detector._find_intersections([a, b], (400, 400))
        assert len(result) == 0

    def test_empty_lines(self, detector: LineDetector):
        assert detector._find_intersections([], (400, 400)) == []


class TestToDomain:
    def test_classifies_angle_0(self, detector: LineDetector):
        line = RawLine(0, 100, 100, 100)
        seg = detector._to_domain(line)
        assert seg.category == LineCategory.HORIZONTAL
        assert seg.angle == 0.0

    def test_classifies_angle_90(self, detector: LineDetector):
        line = RawLine(100, 0, 100, 100)
        seg = detector._to_domain(line)
        assert seg.category == LineCategory.VERTICAL
        assert 85 <= seg.angle <= 95

    def test_classifies_diagonal(self, detector: LineDetector):
        line = RawLine(0, 0, 100, 100)
        seg = detector._to_domain(line)
        assert seg.category == LineCategory.DIAGONAL
        assert 40 <= seg.angle <= 50


class TestAreCollinearAndClose:
    def test_horizontal_close(self, detector: LineDetector):
        a = LineSegment(id=__import__("uuid").uuid4(), x1=0, y1=100, x2=50, y2=100,
                        angle=0.0, length=50.0, category=LineCategory.HORIZONTAL)
        b = LineSegment(id=__import__("uuid").uuid4(), x1=55, y1=100, x2=105, y2=100,
                        angle=0.0, length=50.0, category=LineCategory.HORIZONTAL)
        assert detector._are_collinear_and_close(a, b) is True

    def test_horizontal_far(self, detector: LineDetector):
        a = LineSegment(id=__import__("uuid").uuid4(), x1=0, y1=100, x2=50, y2=100,
                        angle=0.0, length=50.0, category=LineCategory.HORIZONTAL)
        b = LineSegment(id=__import__("uuid").uuid4(), x1=200, y1=100, x2=250, y2=100,
                        angle=0.0, length=50.0, category=LineCategory.HORIZONTAL)
        assert detector._are_collinear_and_close(a, b) is False

    def test_vertical_close(self, detector: LineDetector):
        a = LineSegment(id=__import__("uuid").uuid4(), x1=100, y1=0, x2=100, y2=50,
                        angle=90.0, length=50.0, category=LineCategory.VERTICAL)
        b = LineSegment(id=__import__("uuid").uuid4(), x1=100, y1=55, x2=100, y2=105,
                        angle=90.0, length=50.0, category=LineCategory.VERTICAL)
        assert detector._are_collinear_and_close(a, b) is True

    def test_diagonal_close(self, detector: LineDetector):
        a = LineSegment(id=__import__("uuid").uuid4(), x1=0, y1=0, x2=50, y2=50,
                        angle=45.0, length=70.7, category=LineCategory.DIAGONAL)
        b = LineSegment(id=__import__("uuid").uuid4(), x1=52, y1=52, x2=60, y2=60,
                        angle=45.0, length=11.3, category=LineCategory.DIAGONAL)
        assert detector._are_collinear_and_close(a, b) is True

    def test_different_categories_not_close(self, detector: LineDetector):
        h = LineSegment(id=__import__("uuid").uuid4(), x1=0, y1=100, x2=50, y2=100,
                        angle=0.0, length=50.0, category=LineCategory.HORIZONTAL)
        v = LineSegment(id=__import__("uuid").uuid4(), x1=100, y1=0, x2=100, y2=50,
                        angle=90.0, length=50.0, category=LineCategory.VERTICAL)
        assert detector._are_collinear_and_close(h, v) is False


class TestMergeGroup:
    def test_merge_horizontal(self, detector: LineDetector):
        group = [
            LineSegment(id=__import__("uuid").uuid4(), x1=0, y1=100, x2=50, y2=100,
                        angle=0.0, length=50.0, category=LineCategory.HORIZONTAL),
            LineSegment(id=__import__("uuid").uuid4(), x1=55, y1=102, x2=110, y2=98,
                        angle=2.0, length=55.0, category=LineCategory.HORIZONTAL),
        ]
        merged = detector._merge_group(group)
        assert merged.category == LineCategory.HORIZONTAL
        assert merged.x1 == 0
        assert merged.x2 == 110

    def test_merge_vertical(self, detector: LineDetector):
        group = [
            LineSegment(id=__import__("uuid").uuid4(), x1=100, y1=0, x2=100, y2=50,
                        angle=90.0, length=50.0, category=LineCategory.VERTICAL),
            LineSegment(id=__import__("uuid").uuid4(), x1=102, y1=55, x2=98, y2=110,
                        angle=90.0, length=55.0, category=LineCategory.VERTICAL),
        ]
        merged = detector._merge_group(group)
        assert merged.category == LineCategory.VERTICAL
        assert merged.y1 == 0
        assert merged.y2 == 110

    def test_merge_diagonal(self, detector: LineDetector):
        group = [
            LineSegment(id=__import__("uuid").uuid4(), x1=0, y1=0, x2=30, y2=30,
                        angle=45.0, length=42.4, category=LineCategory.DIAGONAL),
            LineSegment(id=__import__("uuid").uuid4(), x1=35, y1=35, x2=70, y2=70,
                        angle=45.0, length=49.5, category=LineCategory.DIAGONAL),
        ]
        merged = detector._merge_group(group)
        assert merged.category == LineCategory.DIAGONAL
        assert merged.length > 40


class TestDetectWithPrecomputedBinary:
    def test_works_with_shared_preprocessing(self, detector: LineDetector):
        img = _make_blank_image()
        binary = np.full((400, 400), 255, dtype=np.uint8)
        binary[200, 50:350] = 0
        classified1, _, _, _, _ = detector.detect(img, binary=binary)
        classified2, _, _, _, _ = detector.detect(img, binary=binary)
        assert len(classified1) == len(classified2)
