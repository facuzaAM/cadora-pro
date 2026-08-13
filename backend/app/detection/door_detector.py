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
        diag = math.hypot(w, h)
        # Scale door width bounds to image size so low-res AI plans work.
        min_dw = max(MIN_DOOR_W, int(diag * 0.012))
        max_dw = min(MAX_DOOR_W, max(MAX_DOOR_W + 100, int(diag * 0.18)))
        threshold = self._compute_threshold(gray)

        walls = [line for line in grouped_lines
                 if line.category in (LineCategory.HORIZONTAL, LineCategory.VERTICAL)
                 and line.length > min_dw]

        leaf_candidates = [line for line in all_lines
                           if min_dw <= line.length <= max_dw * 1.5
                           and not self._is_wall_edge(line, gray, threshold)]

        self._min_dw = min_dw
        self._max_dw = max_dw

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
    def _line_stroke_bounds(
        gray: np.ndarray, line: LineSegment, threshold: float,
    ) -> tuple[int, int]:
        """Return the perpendicular dark-run bounds of the line's own stroke.

        Works even when the detected centreline is a pixel or two off the
        true stroke: we first snap to the nearest dark pixel at the midpoint,
        then walk out to the contiguous run's edges.
        """
        h, w = gray.shape[:2]
        if line.category == LineCategory.VERTICAL:
            x = int(round((line.x1 + line.x2) / 2.0))
            y = int(round((line.y1 + line.y2) / 2.0))
            if not (0 <= y < h) or x < 0 or x >= w:
                return 0, -1
            row = gray[y]
            lo, hi = x, x
            for d in range(0, 16):
                if 0 <= x - d < w and row[x - d] < threshold:
                    lo = x - d
                    break
            for d in range(0, 16):
                if 0 <= x + d < w and row[x + d] < threshold:
                    hi = x + d
                    break
            if row[lo] >= threshold:  # no ink at all near the centreline
                return 0, -1
            while lo > 0 and row[lo - 1] < threshold:
                lo -= 1
            while hi < w - 1 and row[hi + 1] < threshold:
                hi += 1
            return lo, hi
        # HORIZONTAL
        y = int(round((line.y1 + line.y2) / 2.0))
        x = int(round((line.x1 + line.x2) / 2.0))
        if not (0 <= x < w) or y < 0 or y >= h:
            return 0, -1
        col = gray[:, x]
        lo, hi = y, y
        for d in range(0, 16):
            if 0 <= y - d < h and col[y - d] < threshold:
                lo = y - d
                break
        for d in range(0, 16):
            if 0 <= y + d < h and col[y + d] < threshold:
                hi = y + d
                break
        if col[lo] >= threshold:
            return 0, -1
        while lo > 0 and col[lo - 1] < threshold:
            lo -= 1
        while hi < h - 1 and col[hi + 1] < threshold:
            hi += 1
        return lo, hi

    @staticmethod
    def _is_wall_edge(line: LineSegment, gray: np.ndarray, threshold: float) -> bool:
        if line.category not in (LineCategory.HORIZONTAL, LineCategory.VERTICAL):
            return False

        # A leaf is rejected when a parallel stroke runs immediately next to
        # it (double-line wall). We locate the line's own stroke and probe
        # beyond its edge, so the result is robust to centreline offsets.
        stroke_lo, stroke_hi = DoorDetector._line_stroke_bounds(gray, line, threshold)
        if stroke_lo > stroke_hi:
            return False
        if line.category == LineCategory.VERTICAL:
            y_min, y_max = min(line.y1, line.y2), max(line.y1, line.y2)
            if y_max - y_min < 20:
                return False
            left = DoorDetector._beyond_stroke_counts(
                gray, stroke_lo - 1, -1, y_min, y_max, threshold,
                is_horizontal=False,
            )
            right = DoorDetector._beyond_stroke_counts(
                gray, stroke_hi + 1, 1, y_min, y_max, threshold,
                is_horizontal=False,
            )
            return left >= 2 or right >= 2

        else:  # HORIZONTAL
            x_min, x_max = min(line.x1, line.x2), max(line.x1, line.x2)
            if x_max - x_min < 20:
                return False
            up = DoorDetector._beyond_stroke_counts(
                gray, stroke_lo - 1, -1, x_min, x_max, threshold,
                is_horizontal=True,
            )
            down = DoorDetector._beyond_stroke_counts(
                gray, stroke_hi + 1, 1, x_min, x_max, threshold,
                is_horizontal=True,
            )
            return up >= 2 or down >= 2

    @staticmethod
    def _beyond_stroke_counts(
        gray: np.ndarray, start: int, direction: int, lo: int, hi: int,
        threshold: float, is_horizontal: bool,
    ) -> int:
        """Count sample points that see a parallel stroke beyond `start`.

        Probes a few px outward from the line's own stroke edge; if nothing
        dark is found within the probe window the line is an isolated leaf.
        """
        h, w = gray.shape[:2]
        hits = 0
        for t in [0.2, 0.5, 0.8]:
            along = int(lo + t * (hi - lo))
            found = False
            for d in range(0, 12):
                if is_horizontal:
                    coord = start + direction * d
                    if coord < 0 or coord >= h:
                        break
                    found = gray[coord, along] < threshold
                else:
                    coord = start + direction * d
                    if coord < 0 or coord >= w:
                        break
                    found = gray[along, coord] < threshold
                if found:
                    break
            if found:
                hits += 1
        return hits

    @staticmethod
    def _band_is_dark(
        gray: np.ndarray, fixed_coord: int, p: int,
        is_horizontal: bool, threshold: float, radius: int = 2,
    ) -> bool:
        """True when any pixel in the ±radius band is dark.

        Scans a small band instead of a single pixel so the result is robust
        to walls whose centerline is a few pixels off the detector's ideal
        position, while still detecting 1px-thin walls.
        """
        h, w = gray.shape[:2]
        if is_horizontal:
            lo = max(0, fixed_coord - radius)
            hi = min(h - 1, fixed_coord + radius)
            band = gray[lo:hi + 1, p]
        else:
            lo = max(0, fixed_coord - radius)
            hi = min(w - 1, fixed_coord + radius)
            band = gray[p, lo:hi + 1]
        if band.size == 0:
            return False
        return bool(np.min(band) < threshold)

    def _find_gap_on_line(
        self, gray: np.ndarray, fixed_coord: int,
        scan_start: int, scan_end: int,
        hinge_pos: int, is_horizontal: bool = True,
        threshold: float = 128.0,
    ) -> tuple[int | None, int | None]:
        mw = self._max_dw if hasattr(self, '_max_dw') else MAX_DOOR_W
        h, w = gray.shape[:2]
        lo = max(0, scan_start - mw)
        hi = min((w if is_horizontal else h) - 1, scan_end + mw)
        runs: list[tuple[int, int]] = []
        in_gap = False
        start = lo
        for p in range(lo, hi + 1):
            is_white = not DoorDetector._band_is_dark(
                gray, fixed_coord, p, is_horizontal, threshold,
            )
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
            mn = self._min_dw if hasattr(self, '_min_dw') else MIN_DOOR_W
            gap_width = e - s
            if gap_width < mn or gap_width > mw:
                continue
            # A real doorway is flanked by wall on both sides. Reject runs
            # that bleed into the background beyond the wall's own extent
            # (e.g. the area above the top wall of a plan).
            if s <= lo or e >= hi:
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
                if 0 <= cy < h:
                    band = gray[max(0, cy - 2):min(h, cy + 3), x]
                    dark = bool(np.min(band) < threshold) if band.size else False
                else:
                    dark = False
                if dark:
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
                if 0 <= cx < w:
                    band = gray[y, max(0, cx - 2):min(w, cx + 3)]
                    dark = bool(np.min(band) < threshold) if band.size else False
                else:
                    dark = False
                if dark:
                    if not in_dark:
                        dark_runs += 1
                        in_dark = True
                else:
                    in_dark = False
            return dark_runs >= 2
