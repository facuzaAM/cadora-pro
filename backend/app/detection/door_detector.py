from __future__ import annotations

import math
from uuid import uuid4

import numpy as np

from app.detection.schemas import (
    Door,
    DoorArc,
    DoorDetectionResult,
    DoorType,
    LineCategory,
    LineSegment,
)

MIN_DOOR_W = 15
MAX_DOOR_W = 200
ARC_MIN_R = 10
ARC_MAX_R = 150


class DoorDetector:
    """Detects doors by scanning for gaps in walls and matching
    perpendicular leaf lines from the Hough line detector."""

    def detect(
        self,
        image: np.ndarray,
        grouped_lines: list[LineSegment],
        all_lines: list[LineSegment],
        binary: np.ndarray | None = None,
    ) -> DoorDetectionResult:
        gray = self._preprocess(image) if binary is None else binary
        h, w = image.shape[:2]
        threshold = self._compute_threshold(gray)

        walls = [line for line in grouped_lines
                 if line.category in (LineCategory.HORIZONTAL, LineCategory.VERTICAL)
                 and line.length > MIN_DOOR_W]

        leaf_candidates = [line for line in all_lines
                           if MIN_DOOR_W <= line.length <= MAX_DOOR_W * 1.5
                           and not self._is_wall_edge(line, gray, threshold)]

        doors: list[Door] = []
        used_leaf_ids: set[str] = set()

        for leaf in sorted(leaf_candidates, key=lambda x: x.length, reverse=True):
            leaf_key = f"{leaf.x1:.1f}_{leaf.y1:.1f}_{leaf.x2:.1f}_{leaf.y2:.1f}"
            if leaf_key in used_leaf_ids:
                continue
            door = self._leaf_to_door(leaf, walls, gray, threshold)
            if door is not None:
                doors.append(door)
                used_leaf_ids.add(leaf_key)

        doors = self._deduplicate_doors(doors)
        doors = self._classify_double_doors(doors)
        doors = self._classify_sliding_doors(doors, gray)

        return DoorDetectionResult(doors=doors, image_width=w, image_height=h)

    @staticmethod
    def _preprocess(image: np.ndarray) -> np.ndarray:
        from app.ocr.preprocessor import ImagePreprocessor
        return ImagePreprocessor().detect_pipeline(image)

    @staticmethod
    def _compute_threshold(gray: np.ndarray) -> float:
        """Compute adaptive dark/bright threshold from image."""
        std = float(np.std(gray))
        if std < 10:
            return 128.0
        mean = float(np.mean(gray))
        return max(80.0, min(180.0, mean))

    @staticmethod
    def _is_wall_edge(line: LineSegment, gray: np.ndarray, threshold: float) -> bool:
        if line.category not in (LineCategory.HORIZONTAL, LineCategory.VERTICAL):
            return False

        if line.category == LineCategory.VERTICAL:
            x = int(round((line.x1 + line.x2) / 2.0))
            y_min, y_max = min(line.y1, line.y2), max(line.y1, line.y2)
            if y_max - y_min < 20:
                return False
            left_counts = 0
            right_counts = 0
            for t in [0.2, 0.5, 0.8]:
                y = int(y_min + t * (y_max - y_min))
                if y < 0 or y >= gray.shape[0] or x < 2 or x > gray.shape[1] - 3:
                    continue
                if gray[y, x - 2] < threshold:
                    left_counts += 1
                if gray[y, x + 2] < threshold:
                    right_counts += 1
            return left_counts >= 2 or right_counts >= 2

        else:  # HORIZONTAL
            y = int(round((line.y1 + line.y2) / 2.0))
            x_min, x_max = min(line.x1, line.x2), max(line.x1, line.x2)
            if x_max - x_min < 20:
                return False
            up_counts = 0
            down_counts = 0
            for t in [0.2, 0.5, 0.8]:
                x = int(x_min + t * (x_max - x_min))
                if y < 2 or y > gray.shape[0] - 3 or x < 0 or x >= gray.shape[1]:
                    continue
                if gray[y - 2, x] < threshold:
                    up_counts += 1
                if gray[y + 2, x] < threshold:
                    down_counts += 1
            return up_counts >= 2 or down_counts >= 2

    @staticmethod
    def _find_gap_on_line(
        gray: np.ndarray, fixed_coord: int,
        scan_start: int, scan_end: int,
        hinge_pos: int, is_horizontal: bool = True,
        threshold: float = 128.0,
    ) -> tuple[int | None, int | None]:
        h, w = gray.shape[:2]
        lo = max(0, scan_start - MAX_DOOR_W)
        hi = min((w if is_horizontal else h) - 1, scan_end + MAX_DOOR_W)
        runs: list[tuple[int, int]] = []
        in_gap = False
        start = lo
        for p in range(lo, hi + 1):
            if is_horizontal:
                is_white = gray[fixed_coord, p] > threshold
            else:
                is_white = gray[p, fixed_coord] > threshold
            if is_white and not in_gap:
                start = p
                in_gap = True
            elif not is_white and in_gap:
                runs.append((start, p - 1))
                in_gap = False
        if in_gap:
            runs.append((start, hi))

        best: tuple[int, int] | None = None
        best_dist = float("inf")
        for s, e in runs:
            w = e - s
            if w < MIN_DOOR_W or w > MAX_DOOR_W:
                continue
            d = abs((s + e) / 2.0 - hinge_pos)
            if d < best_dist:
                best_dist = d
                best = (s, e)

        return (best[0], best[1]) if best is not None else (None, None)

    # ── leaf -> door matching ──────────────────────────────────────────

    def _leaf_to_door(
        self, leaf: LineSegment, walls: list[LineSegment], gray: np.ndarray,
        threshold: float,
    ) -> Door | None:
        if leaf.category == LineCategory.VERTICAL:
            return self._vertical_leaf_to_door(leaf, walls, gray, threshold)
        elif leaf.category == LineCategory.HORIZONTAL:
            return self._horizontal_leaf_to_door(leaf, walls, gray, threshold)
        return None

    def _vertical_leaf_to_door(
        self, leaf: LineSegment, walls: list[LineSegment], gray: np.ndarray,
        threshold: float,
    ) -> Door | None:
        lx = (leaf.x1 + leaf.x2) / 2.0
        ly_min = min(leaf.y1, leaf.y2)
        ly_max = max(leaf.y1, leaf.y2)

        for w in walls:
            if w.category != LineCategory.HORIZONTAL:
                continue
            wy = (w.y1 + w.y2) / 2.0
            wx1, wx2 = min(w.x1, w.x2), max(w.x1, w.x2)

            # Leaf must be near the wall
            dist_to_wall = min(abs(wy - ly_min), abs(wy - ly_max))
            if dist_to_wall > 25:
                continue
            # Leaf must be within wall x-range
            if lx < wx1 - 40 or lx > wx2 + 40:
                continue

            # Determine which end touches the wall
            if abs(wy - ly_min) < abs(wy - ly_max):
                hinge_y, tip_y = ly_min, ly_max
            else:
                hinge_y, tip_y = ly_max, ly_min
            hinge_x = lx
            tip_x = lx  # vertical leaf

            gap_start, gap_end = self._find_gap_on_line(
                gray, int(round(wy)), int(round(wx1)), int(round(wx2)),
                int(round(hinge_x)), threshold=threshold,
            )
            if gap_start is None:
                continue
            gap_w = gap_end - gap_start

            dist_to_gap = min(abs(hinge_x - gap_start), abs(hinge_x - gap_end))
            if dist_to_gap > 40:
                continue

            return self._make_door(
                leaf, hinge_x, hinge_y, tip_x, tip_y,
                gap_start, wy, gap_end, wy, gap_w, gray, threshold,
            )

        return None

    def _horizontal_leaf_to_door(
        self, leaf: LineSegment, walls: list[LineSegment], gray: np.ndarray,
        threshold: float,
    ) -> Door | None:
        ly = (leaf.y1 + leaf.y2) / 2.0
        lx_min = min(leaf.x1, leaf.x2)
        lx_max = max(leaf.x1, leaf.x2)

        for w in walls:
            if w.category != LineCategory.VERTICAL:
                continue
            wx = (w.x1 + w.x2) / 2.0
            wy1, wy2 = min(w.y1, w.y2), max(w.y1, w.y2)

            dist_to_wall = min(abs(wx - lx_min), abs(wx - lx_max))
            if dist_to_wall > 25:
                continue
            if ly < wy1 - 40 or ly > wy2 + 40:
                continue

            if abs(wx - lx_min) < abs(wx - lx_max):
                hinge_x, tip_x = lx_min, lx_max
            else:
                hinge_x, tip_x = lx_max, lx_min
            hinge_y = ly
            tip_y = ly

            gap_start, gap_end = self._find_gap_on_line(
                gray, int(round(wx)), int(round(wy1)), int(round(wy2)),
                int(round(hinge_y)), is_horizontal=False, threshold=threshold,
            )
            if gap_start is None:
                continue
            gap_w = gap_end - gap_start

            dist_to_gap = min(abs(hinge_y - gap_start), abs(hinge_y - gap_end))
            if dist_to_gap > 40:
                continue

            return self._make_door(
                leaf, hinge_x, hinge_y, tip_x, tip_y,
                wx, gap_start, wx, gap_end, gap_w, gray, threshold,
            )

        return None

    # ── door construction ──────────────────────────────────────────────

    def _make_door(
        self, leaf: LineSegment,
        hx: float, hy: float, tx: float, ty: float,
        gx1: float, gy1: float, gx2: float, gy2: float,
        gap_w: float, gray: np.ndarray, threshold: float,
    ) -> Door:
        dx, dy = tx - hx, ty - hy
        leaf_len = math.sqrt(dx ** 2 + dy ** 2)
        rotation = 90.0 if leaf.category == LineCategory.VERTICAL else 0.0

        arc = self._detect_arc(gray, hx, hy, tx, ty, threshold)

        swing = ("down" if dy > 0 else "up") if abs(dy) > abs(
            dx
        ) else ("right" if dx > 0 else "left")

        return Door(
            id=uuid4(), type=DoorType.SINGLE,
            x=(gx1 + gx2) / 2.0, y=(gy1 + gy2) / 2.0,
            width=round(gap_w, 1),
            rotation=rotation,
            hinge_x=hx, hinge_y=hy,
            leaf_length=round(leaf_len, 1),
            leaf_x1=tx, leaf_y1=ty,
            leaf_x2=hx, leaf_y2=hy,
            wall_gap_x1=gx1, wall_gap_y1=gy1,
            wall_gap_x2=gx2, wall_gap_y2=gy2,
            swing=swing, arc=arc,
            confidence=0.7 if arc else 0.55,
        )

    def _detect_arc(
        self, gray: np.ndarray,
        hx: float, hy: float, tx: float, ty: float,
        threshold: float = 128.0,
    ) -> DoorArc | None:
        dx, dy = tx - hx, ty - hy
        radius = math.sqrt(dx ** 2 + dy ** 2) * 0.95
        if radius < ARC_MIN_R or radius > ARC_MAX_R:
            return None

        if abs(dy) > abs(dx):
            if dy > 0:
                sa, ea = 90, 180
            else:
                sa, ea = 270, 360
        else:
            if dx > 0:
                sa, ea = 180, 270
            else:
                sa, ea = 0, 90

        h_img, w_img = gray.shape[:2]
        total, hits = 0, 0
        for deg in range(sa, ea + 1):
            rad = math.radians(deg)
            px = int(round(hx + radius * math.cos(rad)))
            py = int(round(hy + radius * math.sin(rad)))
            if 0 <= px < w_img and 0 <= py < h_img:
                total += 1
                if gray[py, px] < threshold:
                    hits += 1

        if total == 0 or hits / total < 0.15:
            return None

        return DoorArc(
            center_x=round(hx, 1), center_y=round(hy, 1),
            radius=round(radius, 1),
            start_angle=float(sa), end_angle=float(ea),
        )

    @staticmethod
    def _deduplicate_doors(doors: list[Door]) -> list[Door]:
        if len(doors) < 2:
            return doors
        used = [False] * len(doors)
        result: list[Door] = []
        for i, a in enumerate(doors):
            if used[i]:
                continue
            best = i
            for j in range(i + 1, len(doors)):
                if used[j]:
                    continue
                b = doors[j]
                if abs(a.rotation - b.rotation) > 10:
                    continue
                if abs(a.wall_gap_x1 - b.wall_gap_x1) > 5 or abs(a.wall_gap_y1 - b.wall_gap_y1) > 5:
                    continue
                if a.rotation == 0:
                    a1, a2 = a.wall_gap_y1, a.wall_gap_y2
                else:
                    a1, a2 = a.wall_gap_x1, a.wall_gap_x2
                if b.rotation == 0:
                    b1, b2 = b.wall_gap_y1, b.wall_gap_y2
                else:
                    b1, b2 = b.wall_gap_x1, b.wall_gap_x2
                overlap = min(a2, b2) - max(a1, b1)
                if overlap <= 0:
                    continue
                # Same leaf? hinges must be close
                hinge_dist = math.sqrt((a.hinge_x - b.hinge_x)**2 + (a.hinge_y - b.hinge_y)**2)
                if hinge_dist > 20:
                    continue
                if doors[j].confidence > doors[best].confidence or (
                    doors[j].arc is not None and doors[best].arc is None
                ):
                    best = j
                used[j] = True
            result.append(doors[best])
            used[i] = True
        return result

    @staticmethod
    def _classify_double_doors(doors: list[Door]) -> list[Door]:
        if len(doors) < 2:
            return doors
        used = [False] * len(doors)
        result: list[Door] = []
        for i, a in enumerate(doors):
            if used[i]:
                continue
            paired = False
            for j in range(i + 1, len(doors)):
                if used[j]:
                    continue
                b = doors[j]
                if abs(a.rotation - b.rotation) > 10:
                    continue
                if abs(a.wall_gap_x1 - b.wall_gap_x1) > 5 or abs(a.wall_gap_y1 - b.wall_gap_y1) > 5:
                    continue
                if a.rotation == 0:
                    a1, a2 = a.wall_gap_y1, a.wall_gap_y2
                else:
                    a1, a2 = a.wall_gap_x1, a.wall_gap_x2
                if b.rotation == 0:
                    b1, b2 = b.wall_gap_y1, b.wall_gap_y2
                else:
                    b1, b2 = b.wall_gap_x1, b.wall_gap_x2
                gap_between = max(a1, b1) - min(a2, b2)
                if gap_between > 15:
                    continue
                gap_combined = max(a2, b2) - min(a1, b1)
                result.append(Door(
                    id=uuid4(), type=DoorType.DOUBLE,
                    x=(a.x + b.x) / 2.0, y=(a.y + b.y) / 2.0,
                    width=round(gap_combined, 1),
                    rotation=a.rotation,
                    hinge_x=(a.hinge_x + b.hinge_x) / 2.0,
                    hinge_y=(a.hinge_y + b.hinge_y) / 2.0,
                    leaf_length=(a.leaf_length + b.leaf_length) / 2.0,
                    swing="both",
                    confidence=min(a.confidence, b.confidence) + 0.1,
                ))
                used[j] = True
                paired = True
                break
            if not paired:
                result.append(a)
            used[i] = True
        return result

    def _classify_sliding_doors(
        self, doors: list[Door], gray: np.ndarray,
    ) -> list[Door]:
        """Reclassify single doors as SLIDING if the gap contains parallel
        lines (tracks) instead of a swing arc."""
        threshold = self._compute_threshold(gray)
        result: list[Door] = []
        for door in doors:
            if door.type != DoorType.SINGLE or door.arc is not None:
                result.append(door)
                continue
            if self._has_parallel_tracks(door, gray, threshold):
                result.append(Door(
                    id=door.id, type=DoorType.SLIDING,
                    x=door.x, y=door.y, width=door.width,
                    rotation=door.rotation,
                    hinge_x=door.hinge_x, hinge_y=door.hinge_y,
                    leaf_length=door.leaf_length,
                    leaf_x1=door.leaf_x1, leaf_y1=door.leaf_y1,
                    leaf_x2=door.leaf_x2, leaf_y2=door.leaf_y2,
                    wall_gap_x1=door.wall_gap_x1, wall_gap_y1=door.wall_gap_y1,
                    wall_gap_x2=door.wall_gap_x2, wall_gap_y2=door.wall_gap_y2,
                    swing=door.swing,
                    confidence=door.confidence + 0.05,
                ))
            else:
                result.append(door)
        return result

    @staticmethod
    def _has_parallel_tracks(door: Door, gray: np.ndarray, threshold: float) -> bool:
        """Check if a door gap contains 2+ parallel dark lines (sliding tracks)."""
        is_horizontal = door.rotation == 0 or abs(door.rotation) < 45
        if is_horizontal:
            cy = int((door.wall_gap_y1 + door.wall_gap_y2) / 2)
            x1 = int(min(door.wall_gap_x1, door.wall_gap_x2))
            x2 = int(max(door.wall_gap_x1, door.wall_gap_x2))
            if x2 - x1 < MIN_DOOR_W:
                return False
            dark_runs = 0
            in_dark = False
            h, w = gray.shape[:2]
            for x in range(max(0, x1), min(w, x2)):
                pix = float(gray[cy, x]) if 0 <= cy < h else 255
                if pix < threshold:
                    if not in_dark:
                        dark_runs += 1
                        in_dark = True
                else:
                    in_dark = False
            return dark_runs >= 2
        else:
            cx = int((door.wall_gap_x1 + door.wall_gap_x2) / 2)
            y1 = int(min(door.wall_gap_y1, door.wall_gap_y2))
            y2 = int(max(door.wall_gap_y1, door.wall_gap_y2))
            if y2 - y1 < MIN_DOOR_W:
                return False
            dark_runs = 0
            in_dark = False
            h, w = gray.shape[:2]
            for y in range(max(0, y1), min(h, y2)):
                pix = float(gray[y, cx]) if 0 <= cx < w else 255
                if pix < threshold:
                    if not in_dark:
                        dark_runs += 1
                        in_dark = True
                else:
                    in_dark = False
            return dark_runs >= 2
