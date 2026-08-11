from __future__ import annotations

import math
from uuid import uuid4

import numpy as np

from app.detection.schemas import (
    LineCategory,
    LineSegment,
    Orientation,
    Window,
    WindowArc,
    WindowDetectionResult,
    WindowType,
)

MIN_WINDOW_W = 30
MAX_WINDOW_W = 300
MIN_WINDOW_H = 10
MAX_WINDOW_H = 80
MIN_DARK_RATIO = 0.08
ARC_MIN_R = 15
ARC_MAX_R = 120
WALL_HALF = 1
BAND_RADIUS = 2
GLASS_BAND_RADIUS = 4
SOLID_WALL_RATIO = 0.55
STROKE_SCAN_RADIUS = 12
MAX_WALL_STROKE = 10
ARC_HIT_RATIO = 0.12


class WindowDetector:
    """Detects windows by scanning walls for gaps and identifying
    glass/frame lines inside those gaps.

    Detects three types:
      - SLIDING  (corredera):  multiple parallel glass lines
      - FIXED    (fija):       single pane, no opening arc
      - CASEMENT (batiente):   single pane with swing arc
    """

    def detect(
        self,
        image: np.ndarray,
        grouped_lines: list[LineSegment],
        binary: np.ndarray | None = None,
    ) -> WindowDetectionResult:
        gray = self._preprocess(image) if binary is None else binary
        h, w = image.shape[:2]
        threshold = self._compute_threshold(gray)

        walls = [line for line in grouped_lines
                 if line.category in (LineCategory.HORIZONTAL, LineCategory.VERTICAL)]

        windows: list[Window] = []
        seen_gaps: set[str] = set()

        for wall in walls:
            found = self._find_windows_on_wall(wall, gray, threshold)
            for win in found:
                key = f"{win.wall_gap_x1:.0f}_{win.wall_gap_y1:.0f}_"
                key += f"{win.wall_gap_x2:.0f}_{win.wall_gap_y2:.0f}"
                if key in seen_gaps:
                    continue
                if any(self._overlaps(win, prev) for prev in windows):
                    continue
                windows.append(win)
                seen_gaps.add(key)

        return WindowDetectionResult(windows=windows, image_width=w, image_height=h)

    @staticmethod
    def _overlaps(a: Window, b: Window) -> bool:
        """True when two windows share the same wall span within tolerance.

        A wall broken by a door/gap can yield several near-parallel grouped
        lines (one per fragment); each reports the same opening, so windows
        that cover the same gap along the same wall are duplicates.
        """
        if a.orientation != b.orientation:
            return False
        if a.orientation == Orientation.HORIZONTAL:
            if abs(a.y - b.y) > MAX_WALL_STROKE:
                return False
            lo = max(a.wall_gap_x1, b.wall_gap_x1)
            hi = min(a.wall_gap_x2, b.wall_gap_x2)
        else:
            if abs(a.x - b.x) > MAX_WALL_STROKE:
                return False
            lo = max(a.wall_gap_y1, b.wall_gap_y1)
            hi = min(a.wall_gap_y2, b.wall_gap_y2)
        overlap = hi - lo
        shorter = min(a.width, b.width)
        return shorter > 0 and overlap / shorter > 0.5

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

    def _find_windows_on_wall(
        self, wall: LineSegment, gray: np.ndarray, threshold: float,
    ) -> list[Window]:
        h_img, w_img = gray.shape[:2]

        if wall.category == LineCategory.HORIZONTAL:
            center = int(round((wall.y1 + wall.y2) / 2.0))
            lo = max(0, int(min(wall.x1, wall.x2)) - MAX_WINDOW_W)
            hi = min(w_img - 1, int(max(wall.x1, wall.x2)) + MAX_WINDOW_W)
            is_horizontal = True
        else:
            center = int(round((wall.x1 + wall.x2) / 2.0))
            lo = max(0, int(min(wall.y1, wall.y2)) - MAX_WINDOW_W)
            hi = min(h_img - 1, int(max(wall.y1, wall.y2)) + MAX_WINDOW_W)
            is_horizontal = False

        # The grouped wall may be the merged centreline of a double-line wall
        # (CAD style) whose centre carries no ink. Find the actual strokes and
        # scan along each of them for gaps.
        strokes = self._wall_strokes(gray, wall, threshold)
        if not strokes:
            return []

        merged: list[tuple[int, int]] = []
        for offset, thickness in strokes:
            fc = center + offset
            if fc < 0:
                continue
            if is_horizontal and fc >= gray.shape[0]:
                continue
            if not is_horizontal and fc >= gray.shape[1]:
                continue
            radius = max(1, thickness // 2)
            wall_threshold = max(
                0.3, min(0.8, 0.7 * thickness / (2 * radius + 1)),
            )
            gaps = self._find_gaps_at_offset(
                gray, fc, lo, hi, is_horizontal, threshold,
                radius=radius, wall_threshold=wall_threshold,
            )
            merged.extend(gaps)

        merged = self._merge_spans(merged)

        result: list[Window] = []
        for gs, ge in merged:
            gap_w = ge - gs
            if gap_w < MIN_WINDOW_W:
                continue
            win = self._gap_to_window(
                gray, gs, ge, is_horizontal, center, threshold,
            )
            if win is not None:
                result.append(win)
        return result

    @staticmethod
    def _wall_strokes(
        gray: np.ndarray, wall: LineSegment, threshold: float,
    ) -> list[tuple[int, int]]:
        """Return (perpendicular offset from centreline, thickness) per stroke.

        Samples the wall at several points and keeps the profile with the most
        ink, so a sample that falls inside a window gap doesn't hide the wall's
        true stroke structure. Oversized runs (perpendicular walls crossing the
        sample) are discarded so a junction never inflates the wall's strokes.
        """
        if wall.category == LineCategory.HORIZONTAL:
            center = int(round((wall.y1 + wall.y2) / 2.0))
            x_min, x_max = int(min(wall.x1, wall.x2)), int(max(wall.x1, wall.x2))
            is_horizontal = True
        else:
            center = int(round((wall.x1 + wall.x2) / 2.0))
            y_min, y_max = int(min(wall.y1, wall.y2)), int(max(wall.y1, wall.y2))
            is_horizontal = False

        best: list[tuple[int, int]] = []
        best_ink = 0
        for t in (0.1, 0.3, 0.5, 0.7, 0.9):
            along = int(
                (x_min + t * (x_max - x_min))
                if is_horizontal else (y_min + t * (y_max - y_min))
            )
            profile = WindowDetector._perpendicular_profile(
                gray, center, along, is_horizontal, threshold,
            )
            strokes = [
                (int(round((lo + hi) / 2 - center)), hi - lo + 1)
                for lo, hi in profile if hi - lo + 1 <= MAX_WALL_STROKE
            ]
            ink = sum(thickness for _, thickness in strokes)
            if ink > best_ink:
                best_ink = ink
                best = strokes
        return best

    @staticmethod
    def _perpendicular_profile(
        gray: np.ndarray, center: int, along: int,
        is_horizontal: bool, threshold: float,
        radius: int = STROKE_SCAN_RADIUS,
    ) -> list[tuple[int, int]]:
        """Dark runs perpendicular to the wall at a given position.

        Returns [(run_lo, run_hi)] in perpendicular coordinates.
        """
        h, w = gray.shape[:2]
        if is_horizontal:
            lo = max(0, center - radius)
            hi = min(h - 1, center + radius)
            if lo > hi:
                return []
            col = gray[lo:hi + 1, along]
        else:
            lo = max(0, center - radius)
            hi = min(w - 1, center + radius)
            if lo > hi:
                return []
            col = gray[along, lo:hi + 1]
        dark = col < threshold
        runs: list[tuple[int, int]] = []
        i = 0
        n = len(dark)
        while i < n:
            if dark[i]:
                j = i
                while j + 1 < n and dark[j + 1]:
                    j += 1
                runs.append((i, j))
                i = j + 1
            else:
                i += 1
        return [(lo + s, lo + e) for s, e in runs]

    @staticmethod
    def _merge_spans(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
        if not spans:
            return []
        ordered = sorted(spans)
        merged: list[tuple[int, int]] = []
        cur_s, cur_e = ordered[0]
        for s, e in ordered[1:]:
            if s <= cur_e + 4:  # overlapping / nearly-touching gaps
                cur_e = max(cur_e, e)
            else:
                merged.append((cur_s, cur_e))
                cur_s, cur_e = s, e
        merged.append((cur_s, cur_e))
        return merged

    @staticmethod
    def _band_dark_ratio(
        gray: np.ndarray, fixed_coord: int, p: int,
        horizontal: bool, threshold: float, radius: int = BAND_RADIUS,
    ) -> float:
        """Fraction of dark pixels in the ±radius band around the scan line.

        A solid wall has a ratio near 1.0, an empty doorway near 0.0, and a
        window gap with thin glass lines somewhere in between — which lets the
        gap scan distinguish "glass inside a window" from "solid wall".
        """
        h, w = gray.shape[:2]
        if horizontal:
            lo = max(0, fixed_coord - radius)
            hi = min(h - 1, fixed_coord + radius)
            band = gray[lo:hi + 1, p]
        else:
            lo = max(0, fixed_coord - radius)
            hi = min(w - 1, fixed_coord + radius)
            band = gray[p, lo:hi + 1]
        if band.size == 0:
            return 1.0
        return float(np.mean(band < threshold))

    @staticmethod
    def _band_is_dark(
        gray: np.ndarray, fixed_coord: int, p: int,
        horizontal: bool, threshold: float, radius: int = BAND_RADIUS,
    ) -> bool:
        """True when any pixel in the ±radius band is dark.

        Used to detect the presence of glass lines inside a candidate gap;
        the gap boundary itself is decided by ``_band_dark_ratio``.
        """
        h, w = gray.shape[:2]
        if horizontal:
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

    @staticmethod
    def _find_gaps_at_offset(
        gray: np.ndarray, center: int,
        lo: int, hi: int, horizontal: bool,
        threshold: float = 128.0,
        radius: int = BAND_RADIUS,
        wall_threshold: float = SOLID_WALL_RATIO,
    ) -> list[tuple[int, int]]:
        candidates: dict[tuple[int, int], bool] = {}

        limit = gray.shape[1] if horizontal else gray.shape[0]
        lo = max(0, min(lo, limit - 1))
        hi = min(limit - 1, max(hi, 0))
        if hi < lo:
            return []

        fc = center
        if fc < 0:
            return []
        if horizontal and fc >= gray.shape[0]:
            return []
        if not horizontal and fc >= gray.shape[1]:
            return []

        in_gap = False
        start = lo
        p = lo
        while p <= hi:
            is_wall = WindowDetector._band_dark_ratio(
                gray, fc, p, horizontal, threshold, radius,
            ) > wall_threshold
            if not is_wall and not in_gap:
                start = p
                in_gap = True
                p += 1
            elif is_wall and in_gap:
                wp = p - start
                if wp >= MIN_WINDOW_W:
                    left_ok = (start - 1) >= lo
                    right_ok = p <= hi
                    if left_ok and right_ok:
                        left_wall = WindowDetector._band_dark_ratio(
                            gray, fc, start - 1, horizontal, threshold, radius,
                        ) > wall_threshold
                        right_wall = WindowDetector._band_dark_ratio(
                            gray, fc, p, horizontal, threshold, radius,
                        ) > wall_threshold
                        if left_wall and right_wall:
                            candidates[(start, p - 1)] = True
                in_gap = False
            p += 1
        if in_gap:
            wp = hi - start + 1
            if wp >= MIN_WINDOW_W:
                left_ok = (start - 1) >= lo
                if left_ok:
                    left_wall = WindowDetector._band_dark_ratio(
                        gray, fc, start - 1, horizontal, threshold, radius,
                    ) > wall_threshold
                    if left_wall:
                        candidates[(start, hi)] = True

        return list(candidates.keys())

    def _gap_to_window(
        self, gray: np.ndarray,
        gs: int, ge: int,
        is_horizontal: bool, center: int,
        threshold: float,
    ) -> Window | None:
        dark_runs, dark_pixels = self._find_dark_runs(
            gray, center, gs, ge, is_horizontal, threshold,
        )
        gap_w = ge - gs
        dark_ratio = dark_pixels / gap_w if gap_w > 0 else 0

        if dark_ratio < MIN_DARK_RATIO:
            return None

        glass_lines = len(dark_runs)

        wtype, confidence = self._classify_window(
            gray, dark_runs, dark_ratio, gs, ge, is_horizontal, center, threshold,
        )

        gap_center = (gs + ge) / 2.0
        if is_horizontal:
            x, y = gap_center, float(center)
            rotation = 0.0
            orientation = Orientation.HORIZONTAL
        else:
            x, y = float(center), gap_center
            rotation = 90.0
            orientation = Orientation.VERTICAL

        height = self._find_window_height(
            gray, gs, ge, is_horizontal, center, threshold,
        )

        arc_model = None
        if wtype == WindowType.CASEMENT:
            arc_model = self._detect_window_arc(
                gray, gs, ge, is_horizontal, center, threshold,
            )

        return Window(
            id=uuid4(), type=wtype,
            x=round(x, 1), y=round(y, 1),
            width=round(gap_w, 1), height=round(height, 1),
            rotation=rotation,
            orientation=orientation,
            wall_gap_x1=float(gs) if is_horizontal else float(center),
            wall_gap_y1=float(center) if is_horizontal else float(gs),
            wall_gap_x2=float(ge) if is_horizontal else float(center),
            wall_gap_y2=float(center) if is_horizontal else float(ge),
            glass_lines=glass_lines,
            arc=arc_model,
            confidence=round(confidence, 2),
        )

    def _classify_window(
        self, gray: np.ndarray,
        dark_runs: list[tuple[int, int]],
        dark_ratio: float,
        gs: int, ge: int,
        is_horizontal: bool, center: int,
        threshold: float = 128.0,
    ) -> tuple[WindowType, float]:
        # Along-gap runs can collapse into one when the scan band covers both
        # glass strokes, so count the glass perpendicular to the wall too.
        gap_center = (gs + ge) / 2.0
        perp_runs = self._perpendicular_profile(
            gray, center, int(round(gap_center)), is_horizontal, threshold,
            radius=GLASS_BAND_RADIUS,
        )
        glass_lines = max(len(dark_runs), len(perp_runs))

        if glass_lines >= 2:
            run_thicknesses = [e - s for s, e in dark_runs]
            avg_thickness = sum(run_thicknesses) / len(run_thicknesses) if run_thicknesses else 0
            if avg_thickness < 6:
                return WindowType.SLIDING, 0.7
            return WindowType.SLIDING, 0.6

        arc = self._detect_window_arc(
            gray, gs, ge, is_horizontal, center, threshold,
        )
        if arc is not None:
            return WindowType.CASEMENT, 0.7

        return WindowType.FIXED, 0.55

    def _find_window_height(
        self, gray: np.ndarray,
        gs: int, ge: int,
        is_horizontal: bool, center: int,
        threshold: float = 128.0,
    ) -> float:
        h_img, w_img = gray.shape[:2]

        if is_horizontal:
            scan_x = int(round((gs + ge) / 2.0))
            scan_y = center
            up_lo = max(0, scan_y - MAX_WINDOW_H)
            down_hi = min(h_img - 1, scan_y + MAX_WINDOW_H)

            up_extent = scan_y
            for y in range(scan_y, up_lo - 1, -1):
                if gray[y, scan_x] < threshold:
                    break
                up_extent = y

            down_extent = scan_y
            for y in range(scan_y, down_hi + 1):
                if gray[y, scan_x] < threshold:
                    break
                down_extent = y

            height = down_extent - up_extent
        else:
            scan_y = int(round((gs + ge) / 2.0))
            scan_x = center
            left_lo = max(0, scan_x - MAX_WINDOW_H)
            right_hi = min(w_img - 1, scan_x + MAX_WINDOW_H)

            left_extent = scan_x
            for x in range(scan_x, left_lo - 1, -1):
                if gray[scan_y, x] < threshold:
                    break
                left_extent = x

            right_extent = scan_x
            for x in range(scan_x, right_hi + 1):
                if gray[scan_y, x] < threshold:
                    break
                right_extent = x

            height = right_extent - left_extent

        return max(float(height), 0.0)

    @staticmethod
    def _find_dark_runs(
        gray: np.ndarray, fixed_coord: int,
        gs: int, ge: int, horizontal: bool,
        threshold: float = 128.0,
    ) -> tuple[list[tuple[int, int]], int]:
        runs: list[tuple[int, int]] = []
        in_run = False
        start = gs
        dark_total = 0
        for p in range(gs, ge + 1):
            is_dark = WindowDetector._band_is_dark(
                gray, fixed_coord, p, horizontal, threshold,
            )
            if is_dark:
                dark_total += 1
            if is_dark and not in_run:
                start = p
                in_run = True
            elif not is_dark and in_run:
                runs.append((start, p - 1))
                in_run = False
        if in_run:
            runs.append((start, ge))
        return runs, dark_total

    def _detect_window_arc(
        self, gray: np.ndarray,
        gs: int, ge: int,
        is_horizontal: bool, fixed_coord: int,
        threshold: float = 128.0,
    ) -> WindowArc | None:
        gap_w = ge - gs
        radius = gap_w * 0.4
        if radius < ARC_MIN_R or radius > ARC_MAX_R:
            return None

        if is_horizontal:
            hx = float(gs)
            hy = float(fixed_coord)
            sa, ea = 100, 170
        else:
            hx = float(fixed_coord)
            hy = float(gs)
            sa, ea = 190, 260

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

        if total == 0 or hits / total < ARC_HIT_RATIO:
            return None

        return WindowArc(
            center_x=round(hx, 1), center_y=round(hy, 1),
            radius=round(radius, 1),
            start_angle=float(sa), end_angle=float(ea),
        )
