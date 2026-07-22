from __future__ import annotations

import math
from dataclasses import dataclass
from uuid import uuid4

import cv2
import numpy as np

from app.detection.schemas import LineCategory, LineSegment, Intersection

ANGLE_TOLERANCE = 5.0
MIN_LINE_LENGTH = 20
GROUP_DISTANCE_THRESHOLD = 30


@dataclass
class RawLine:
    x1: int
    y1: int
    x2: int
    y2: int


class LineDetector:
    """Detects, classifies and groups lines in floor-plan images.

    Handles CAD exports, scanned paper plans, and AI-generated images.
    """

    def detect(
        self, image: np.ndarray
    ) -> tuple[list[LineSegment], list[Intersection], int, int]:
        binary = self._preprocess(image)
        edges = self._edge_detection(binary)
        raw = self._hough_lines(edges)
        filtered = self._filter_noise(raw)
        classified = [self._to_domain(l) for l in filtered]
        grouped = self._group_collinear(classified)
        intersections = self._find_intersections(grouped, image.shape)

        h, w = image.shape[:2]
        return classified, grouped, intersections, w, h

    # ── preprocessing ───────────────────────────────────────────────────

    def _preprocess(self, image: np.ndarray) -> np.ndarray:
        """Multi-stage preprocessing that handles any image source."""
        from app.ocr.preprocessor import ImagePreprocessor
        pp = ImagePreprocessor()
        return pp.detect_pipeline(image)

    def _edge_detection(self, image: np.ndarray) -> np.ndarray:
        # Compute dynamic thresholds from image statistics
        mean_val = float(np.mean(image))
        low = max(30, int(mean_val * 0.3))
        high = min(200, int(mean_val * 0.8))

        edges = cv2.Canny(image, low, high, apertureSize=3)

        # Dilate to reconnect broken junctions
        kernel = np.ones((2, 2), np.uint8)
        return cv2.dilate(edges, kernel, iterations=1)

    def _hough_lines(self, edges: np.ndarray) -> list[RawLine]:
        h, w = edges.shape[:2]
        # Adapt minLineLength to image size (1-2% of diagonal)
        diag = math.sqrt(h ** 2 + w ** 2)
        adaptive_min_len = max(15, int(diag * 0.01))
        adaptive_gap = max(5, int(diag * 0.005))

        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=math.pi / 180,
            threshold=40,
            minLineLength=adaptive_min_len,
            maxLineGap=adaptive_gap,
        )
        if lines is None:
            return []
        return [
            RawLine(x1=int(l[0]), y1=int(l[1]), x2=int(l[2]), y2=int(l[3]))
            for l in lines
        ]

    # ── filtering ───────────────────────────────────────────────────────

    def _filter_noise(self, lines: list[RawLine]) -> list[RawLine]:
        return [l for l in lines if self._line_length(l) >= MIN_LINE_LENGTH]

    # ── classification ──────────────────────────────────────────────────

    @staticmethod
    def _line_length(line: RawLine) -> float:
        return math.sqrt((line.x2 - line.x1) ** 2 + (line.y2 - line.y1) ** 2)

    @staticmethod
    def _line_angle(line: RawLine) -> float:
        dx = line.x2 - line.x1
        dy = line.y2 - line.y1
        return math.degrees(math.atan2(abs(dy), dx))

    def _classify_angle(self, angle: float) -> LineCategory:
        if angle <= ANGLE_TOLERANCE or angle >= 180 - ANGLE_TOLERANCE:
            return LineCategory.HORIZONTAL
        if 90 - ANGLE_TOLERANCE <= angle <= 90 + ANGLE_TOLERANCE:
            return LineCategory.VERTICAL
        return LineCategory.DIAGONAL

    def _to_domain(self, line: RawLine) -> LineSegment:
        angle = self._line_angle(line)
        return LineSegment(
            id=uuid4(),
            x1=float(line.x1), y1=float(line.y1),
            x2=float(line.x2), y2=float(line.y2),
            angle=round(angle, 2),
            length=round(self._line_length(line), 2),
            category=self._classify_angle(angle),
        )

    # ── grouping collinear segments ─────────────────────────────────────

    def _group_collinear(self, lines: list[LineSegment]) -> list[LineSegment]:
        if not lines:
            return []
        result: list[LineSegment] = []
        for cat in LineCategory:
            cat_lines = [l for l in lines if l.category == cat]
            if cat_lines:
                result.extend(self._merge_collinear(cat_lines))
        return result

    def _merge_collinear(self, lines: list[LineSegment]) -> list[LineSegment]:
        if len(lines) <= 1:
            return lines

        used = [False] * len(lines)
        merged: list[LineSegment] = []

        for i in range(len(lines)):
            if used[i]:
                continue
            group = [lines[i]]
            used[i] = True
            for j in range(i + 1, len(lines)):
                if used[j]:
                    continue
                if self._are_collinear_and_close(lines[i], lines[j]):
                    group.append(lines[j])
                    used[j] = True
            if len(group) == 1:
                merged.append(group[0])
            else:
                merged.append(self._merge_group(group))
        return merged

    def _are_collinear_and_close(self, a: LineSegment, b: LineSegment) -> bool:
        angle_diff = abs(a.angle - b.angle)
        if angle_diff > ANGLE_TOLERANCE and abs(angle_diff - 180) > ANGLE_TOLERANCE:
            return False

        if a.category == LineCategory.HORIZONTAL and b.category == LineCategory.HORIZONTAL:
            y_dist = min(
                abs(a.y1 - b.y1), abs(a.y1 - b.y2),
                abs(a.y2 - b.y1), abs(a.y2 - b.y2),
            )
            if y_dist > GROUP_DISTANCE_THRESHOLD / 2:
                return False
            ax_min, ax_max = min(a.x1, a.x2), max(a.x1, a.x2)
            bx_min, bx_max = min(b.x1, b.x2), max(b.x1, b.x2)
            gap = max(ax_min, bx_min) - min(ax_max, bx_max)
            return gap <= GROUP_DISTANCE_THRESHOLD

        if a.category == LineCategory.VERTICAL and b.category == LineCategory.VERTICAL:
            x_dist = min(
                abs(a.x1 - b.x1), abs(a.x1 - b.x2),
                abs(a.x2 - b.x1), abs(a.x2 - b.x2),
            )
            if x_dist > GROUP_DISTANCE_THRESHOLD / 2:
                return False
            ay_min, ay_max = min(a.y1, a.y2), max(a.y1, a.y2)
            by_min, by_max = min(b.y1, b.y2), max(b.y1, b.y2)
            gap = max(ay_min, by_min) - min(ay_max, by_max)
            return gap <= GROUP_DISTANCE_THRESHOLD

        return False

    def _merge_group(self, group: list[LineSegment]) -> LineSegment:
        xs = [p for l in group for p in (l.x1, l.x2)]
        ys = [p for l in group for p in (l.y1, l.y2)]
        cat = group[0].category

        if cat == LineCategory.HORIZONTAL:
            y = sum(ys) / len(ys)
            return LineSegment(
                id=uuid4(), x1=min(xs), y1=y, x2=max(xs), y2=y,
                angle=0.0, length=max(xs) - min(xs), category=cat,
            )
        if cat == LineCategory.VERTICAL:
            x = sum(xs) / len(xs)
            return LineSegment(
                id=uuid4(), x1=x, y1=min(ys), x2=x, y2=max(ys),
                angle=90.0, length=max(ys) - min(ys), category=cat,
            )

        farthest = self._farthest_points(group)
        return LineSegment(
            id=uuid4(),
            x1=farthest[0][0], y1=farthest[0][1],
            x2=farthest[1][0], y2=farthest[1][1],
            angle=round(self._line_angle(RawLine(
                int(farthest[0][0]), int(farthest[0][1]),
                int(farthest[1][0]), int(farthest[1][1]),
            )), 2),
            length=round(farthest[2], 2),
            category=cat,
        )

    @staticmethod
    def _farthest_points(
        group: list[LineSegment],
    ) -> tuple[tuple[float, float], tuple[float, float], float]:
        pts = [(l.x1, l.y1) for l in group] + [(l.x2, l.y2) for l in group]
        best = (0.0, (0.0, 0.0), (0.0, 0.0))
        for i, p1 in enumerate(pts):
            for p2 in pts[i + 1:]:
                d = math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)
                if d > best[0]:
                    best = (d, p1, p2)
        return (best[1], best[2], best[0])

    # ── intersections ───────────────────────────────────────────────────

    def _find_intersections(
        self, lines: list[LineSegment], shape: tuple[int, ...]
    ) -> list[Intersection]:
        h, w = shape[:2] if len(shape) >= 2 else (0, 0)
        result: list[Intersection] = []

        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                pt = self._segment_intersection(lines[i], lines[j])
                if pt is None:
                    continue
                x, y = pt
                if not (0 <= x <= w and 0 <= y <= h):
                    continue

                nearby = self._find_nearby(result, x, y, 5)
                if nearby is not None:
                    for lid in (lines[i].id, lines[j].id):
                        if lid not in nearby.lines:
                            nearby.lines.append(lid)
                else:
                    result.append(Intersection(
                        id=uuid4(),
                        x=round(x, 1), y=round(y, 1),
                        lines=[lines[i].id, lines[j].id],
                    ))
        return result

    @staticmethod
    def _segment_intersection(
        a: LineSegment, b: LineSegment,
    ) -> tuple[float, float] | None:
        x1, y1, x2, y2 = a.x1, a.y1, a.x2, a.y2
        x3, y3, x4, y4 = b.x1, b.y1, b.x2, b.y2

        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-8:
            return None

        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

        if 0 <= t <= 1 and 0 <= u <= 1:
            return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
        return None

    @staticmethod
    def _has_nearby(
        intersections: list[Intersection], x: float, y: float, threshold: float = 5.0,
    ) -> bool:
        return any(
            math.sqrt((i.x - x) ** 2 + (i.y - y) ** 2) < threshold
            for i in intersections
        )

    @staticmethod
    def _find_nearby(
        intersections: list[Intersection], x: float, y: float, threshold: float = 5.0,
    ) -> Intersection | None:
        for i in intersections:
            if math.sqrt((i.x - x) ** 2 + (i.y - y) ** 2) < threshold:
                return i
        return None
