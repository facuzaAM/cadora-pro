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
                if key not in seen_gaps:
                    windows.append(win)
                    seen_gaps.add(key)

        return WindowDetectionResult(windows=windows, image_width=w, image_height=h)

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

        gaps = self._find_gaps_at_offset(gray, center, lo, hi, is_horizontal, threshold)

        result: list[Window] = []
        for gs, ge in gaps:
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
    def _find_gaps_at_offset(
        gray: np.ndarray, center: int,
        lo: int, hi: int, horizontal: bool,
        threshold: float = 128.0,
    ) -> list[tuple[int, int]]:
        candidates: set[tuple[int, int]] = {}

        for offset in [WALL_HALF, -WALL_HALF]:
            fc = center + offset
            if fc < 0:
                continue
            if horizontal and fc >= gray.shape[0]:
                continue
            if not horizontal and fc >= gray.shape[1]:
                continue

            in_gap = False
            start = lo
            p = lo
            while p <= hi:
                is_wall = gray[fc, p] < threshold if horizontal else gray[p, fc] < threshold
                if not is_wall and not in_gap:
                    start = p
                    in_gap = True
                    p += 1
                elif is_wall and in_gap:
                    thin_line = False
                    if p + 1 <= hi:
                        if horizontal:
                            next_pix = gray[fc, p + 1] < threshold
                        else:
                            next_pix = gray[p + 1, fc] < threshold
                        if not next_pix:
                            thin_line = True
                    if thin_line:
                        p += 1
                        continue
                    wp = p - start
                    if wp >= MIN_WINDOW_W:
                        left_ok = (start - 1) >= lo
                        right_ok = p <= hi
                        if left_ok and right_ok:
                            if horizontal:
                                left_wall = gray[fc, start - 1] < threshold
                                right_wall = gray[fc, p] < threshold
                            else:
                                left_wall = gray[start - 1, fc] < threshold
                                right_wall = gray[p, fc] < threshold
                            if left_wall and right_wall:
                                candidates[(start, p - 1)] = True
                    in_gap = False
                p += 1
            if in_gap:
                wp = hi - start + 1
                if wp >= MIN_WINDOW_W:
                    left_ok = (start - 1) >= lo
                    if left_ok:
                        if horizontal:
                            left_wall = gray[fc, start - 1] < threshold
                        else:
                            left_wall = gray[start - 1, fc] < threshold
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
        glass_lines = len(dark_runs)

        if glass_lines >= 2:
            run_thicknesses = [e - s for s, e in dark_runs]
            avg_thickness = sum(run_thicknesses) / len(run_thicknesses)
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
            if horizontal:
                is_dark = gray[fixed_coord, p] < threshold
            else:
                is_dark = gray[p, fixed_coord] < threshold
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
