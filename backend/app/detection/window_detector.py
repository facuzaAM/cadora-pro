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
BAND_RADIUS = 2
GLASS_BAND_RADIUS = 4
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
        excluded_gaps: list[tuple[float, float, float, float]] | None = None,
    ) -> WindowDetectionResult:
        gray = self._preprocess(image) if binary is None else binary
        h, w = image.shape[:2]
        threshold = self._compute_threshold(gray)
        excluded_gaps = excluded_gaps or []

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
                # A door's swing arc near its gap can read as a window; a real
                # window never shares the same opening as a door.
                if any(self._gap_overlaps(win, eg) for eg in excluded_gaps):
                    continue
                windows.append(win)
                seen_gaps.add(key)

        return WindowDetectionResult(windows=windows, image_width=w, image_height=h)

    @staticmethod
    def _gap_overlaps(
        win: Window, gap: tuple[float, float, float, float],
    ) -> bool:
        """True when a candidate window gap overlaps an excluded (door) gap."""
        gx1, gy1, gx2, gy2 = gap
        a_hrz = abs(win.wall_gap_x2 - win.wall_gap_x1) >= abs(win.wall_gap_y2 - win.wall_gap_y1)
        b_hrz = abs(gx2 - gx1) >= abs(gy2 - gy1)
        if a_hrz != b_hrz:
            return False
        if a_hrz:
            if abs(win.wall_gap_y1 - gy1) > MAX_WALL_STROKE:
                return False
            lo = max(min(win.wall_gap_x1, win.wall_gap_x2), min(gx1, gx2))
            hi = min(max(win.wall_gap_x1, win.wall_gap_x2), max(gx1, gx2))
        else:
            if abs(win.wall_gap_x1 - gx1) > MAX_WALL_STROKE:
                return False
            lo = max(min(win.wall_gap_y1, win.wall_gap_y2), min(gy1, gy2))
            hi = min(max(win.wall_gap_y1, win.wall_gap_y2), max(gy1, gy2))
        return hi - lo > 0

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
            gaps = self._find_gaps_at_offset(
                gray, fc, lo, hi, is_horizontal, threshold,
                thickness=thickness,
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

        Samples the wall across its whole span and votes on which strokes are
        stable. Real wall strokes appear at the same offset in nearly every
        sample; a window gap's glass lines (two thin strokes whose *combined*
        ink can exceed a solid single-line wall) only appear in the samples
        that fall inside the gap. Picking the highest-ink profile would select
        the glass and fabricate phantom windows everywhere else, so we keep
        only the strokes present in a majority of samples. Oversized runs
        (perpendicular walls crossing the sample) are discarded so a junction
        never inflates the wall's strokes. Returns [] when no stable stroke
        exists (e.g. a phantom wall with no real ink).
        """
        if wall.category == LineCategory.HORIZONTAL:
            center = int(round((wall.y1 + wall.y2) / 2.0))
            span_lo, span_hi = int(min(wall.x1, wall.x2)), int(max(wall.x1, wall.x2))
            is_horizontal = True
        else:
            center = int(round((wall.x1 + wall.x2) / 2.0))
            span_lo, span_hi = int(min(wall.y1, wall.y2)), int(max(wall.y1, wall.y2))
            is_horizontal = False

        span = span_hi - span_lo
        n = min(9, max(5, span // 120))
        if span < 40:
            n = 3

        votes: dict[int, int] = {}
        thickness: dict[int, int] = {}
        positions = [
            int(span_lo + t * span) for t in np.linspace(0.05, 0.95, n)
        ]
        for along in positions:
            profile = WindowDetector._perpendicular_profile(
                gray, center, along, is_horizontal, threshold,
            )
            for lo, hi in profile:
                thick = hi - lo + 1
                if thick > MAX_WALL_STROKE:
                    continue
                off = int(round((lo + hi) / 2 - center))
                # Merge nearby offsets into one stroke cluster (glass lines of
                # a double wall or two window panes sit 2-4px apart).
                if votes:
                    near = min(votes, key=lambda k: abs(k - off))
                    if abs(near - off) <= 3:
                        votes[near] += 1
                        thickness[near] += thick
                        continue
                votes[off] = votes.get(off, 0) + 1
                thickness[off] = thickness.get(off, 0) + thick

        support = max(3, int(n * 0.6))
        return [
            (off, thickness[off] // votes[off])
            for off, count in votes.items() if count >= support
        ]

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
    def _band_is_dark(
        gray: np.ndarray, fixed_coord: int, p: int,
        horizontal: bool, threshold: float, radius: int = BAND_RADIUS,
    ) -> bool:
        """True when any pixel in the ±radius band is dark.

        Used to detect the presence of glass lines inside a candidate gap;
        the gap extent itself is decided by ``_find_gaps_at_offset``.
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
    def _column_is_solid(
        gray: np.ndarray, fc: int, along: int,
        horizontal: bool, threshold: float, thickness: int,
    ) -> bool:
        """True when one dark run spans the wall's full core at this column.

        A solid wall is a single contiguous stroke through its centre, so at
        any column a single dark run covers the whole core (the wall centre
        is solid). A window gap replaces the wall with two thin glass lines
        that leave a white gap at the centre, so no single run covers the
        core. This distinguishes openings (windows/doors) from solid wall
        without a fragile ink-ratio threshold.
        """
        core_r = max(0, (thickness - 1) // 2)
        core_len = 2 * core_r + 1
        lo_c, hi_c = fc - core_r, fc + core_r
        best = 0
        for rlo, rhi in WindowDetector._perpendicular_profile(
            gray, fc, along, horizontal, threshold,
        ):
            overlap = min(rhi, hi_c) - max(rlo, lo_c) + 1
            if overlap > best:
                best = overlap
        # A solid wall covers the core; allow a 1px sub-pixel shift (deskew
        # staircase) to expose one edge row without calling it an opening.
        # Window glass lines leave a gap at the centre, so no single run
        # spans nearly the whole core. For a 1-row core there is no slack, so
        # still require actual ink.
        return best >= max(1, core_len - 1)

    @staticmethod
    def _find_gaps_at_offset(
        gray: np.ndarray, center: int,
        lo: int, hi: int, horizontal: bool,
        threshold: float = 128.0,
        thickness: int = 4,
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
            is_wall = WindowDetector._column_is_solid(
                gray, fc, p, horizontal, threshold, thickness,
            )
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
                        left_wall = WindowDetector._column_is_solid(
                            gray, fc, start - 1, horizontal, threshold, thickness,
                        )
                        right_wall = WindowDetector._column_is_solid(
                            gray, fc, p, horizontal, threshold, thickness,
                        )
                        if left_wall and right_wall:
                            candidates[(start, p - 1)] = True
                in_gap = False
            p += 1
        if in_gap:
            wp = hi - start + 1
            if wp >= MIN_WINDOW_W:
                left_ok = (start - 1) >= lo
                if left_ok:
                    left_wall = WindowDetector._column_is_solid(
                        gray, fc, start - 1, horizontal, threshold, thickness,
                    )
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
