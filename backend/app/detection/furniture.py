"""Post-detection furniture / clutter removal.

AI and photo floor plans are full of furniture (beds, tables, sofas, columns)
whose closed rectangular/circular outlines and interior strokes get detected as
short walls. A real geometry is a bounded region (a room) much larger than a
piece of furniture, so we drop lines that sit inside small, box-like, fully
enclosed shapes that do not touch the image border.

This runs after wall refinement and uses the gap-preserving "fine" binary, so
walls are a clean single stroke and furniture remains a closed box.
"""

from __future__ import annotations

import cv2
import numpy as np

from app.detection.schemas import LineCategory, LineSegment

# Furniture bounding-box must be within this fraction of the plan area: big
# enough to be a real object, small enough that it's not a room.
MIN_FURNITURE_RATIO = 0.003
MAX_FURNITURE_RATIO = 0.10
# A box slimmer than this aspect ratio is a corridor/wall, not furniture.
MAX_ASPECT = 8.0
# A furniture box must not reach the image edge (that's the outer shell).
BORDER_MARGIN = 3
# Padding so a furniture stroke's centreline endpoints fall inside the box.
BOX_PAD = 6


def _is_furniture_box(
    c, plan_area: float, w: int, h: int,
) -> tuple[bool, tuple[int, int, int, int]]:
    """Return (is_furniture, (x1, y1, x2, y2)) for a closed contour.

    Furniture (beds, tables, sofas, columns) are small closed boxes. We use the
    bounding-box size (not the outline area, which for a hollow drawing is tiny)
    and drop the hollow-fill requirement; real rooms are excluded by the upper
    size bound and non-closed partitions never produce a contour box.
    """
    area = cv2.contourArea(c)
    if area <= 60:
        return False, (0, 0, 0, 0)
    x, y, cw, ch = cv2.boundingRect(c)
    b_area = max(1, cw * ch)
    ratio = b_area / max(1.0, plan_area)
    if not (MIN_FURNITURE_RATIO <= ratio <= MAX_FURNITURE_RATIO):
        return False, (0, 0, 0, 0)
    aspect = max(cw, ch) / max(1, min(cw, ch))
    if aspect > MAX_ASPECT:
        return False, (0, 0, 0, 0)
    if x <= BORDER_MARGIN or y <= BORDER_MARGIN:
        return False, (0, 0, 0, 0)
    if x + cw >= w - BORDER_MARGIN or y + ch >= h - BORDER_MARGIN:
        return False, (0, 0, 0, 0)
    box = (max(0, x - BOX_PAD), max(0, y - BOX_PAD),
           min(w - 1, x + cw + BOX_PAD), min(h - 1, y + ch + BOX_PAD))
    return True, box


def _point_in_box(px: float, py: float, box: tuple[int, int, int, int]) -> bool:
    x1, y1, x2, y2 = box
    return x1 <= px <= x2 and y1 <= py <= y2


def _line_in_box(line: LineSegment, box: tuple[int, int, int, int]) -> bool:
    """True when both endpoints fall inside a furniture box.

    Requiring both endpoints keeps real, long walls (which span across the box
    or connect to the shell) intact; furniture strokes live entirely inside.
    """
    return _point_in_box(line.x1, line.y1, box) and _point_in_box(line.x2, line.y2, box)


def remove_furniture(
    lines: list[LineSegment], binary: np.ndarray,
) -> list[LineSegment]:
    """Drop grouped lines that make up closed furniture shapes."""
    if not lines:
        return lines
    h, w = binary.shape[:2]
    plan_area = float(w) * float(h)

    ink = cv2.bitwise_not(binary)
    # RETR_LIST returns every closed contour, including the furniture islands
    # inside the outer shell (RETR_EXTERNAL would swallow them as holes).
    contours, _ = cv2.findContours(ink, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    boxes: list[tuple[int, int, int, int]] = []
    for c in contours:
        is_furniture, box = _is_furniture_box(c, plan_area, w, h)
        if is_furniture:
            boxes.append(box)

    if not boxes:
        return lines

    kept: list[LineSegment] = []
    for line in lines:
        if any(_line_in_box(line, box) for box in boxes):
            continue
        kept.append(line)
    return kept


# ── stairs ──────────────────────────────────────────────────────────────────

# A staircase is many short parallel treads, evenly spaced and of similar
# length. Real walls are long or few; a cluster of >= this many short parallels
# is almost certainly a stair (or similar repetitive hatch pattern).
STAIR_MIN_LEN = 25
STAIR_MAX_LEN = 300
STAIR_SUCCESSIVE_MIN = 3
STAIR_PERP_TOL = 16
STAIR_SPAN_OVERLAP = 0.4
STAIR_SPACING_DEV = 0.45
STAIR_LEN_RATIO = 2.2


def _perpendicular_coord(line: LineSegment) -> float:
    return (line.y1 + line.y2) / 2 if line.category == LineCategory.HORIZONTAL else (
        (line.x1 + line.x2) / 2
    )


def _span(line: LineSegment) -> tuple[float, float]:
    if line.category == LineCategory.HORIZONTAL:
        return min(line.x1, line.x2), max(line.x1, line.x2)
    return min(line.y1, line.y2), max(line.y1, line.y2)


def _same_stair_family(a: LineSegment, b: LineSegment) -> bool:
    """True when two treads lie on the same staircase (overlapping span, similar length).

    Stair treads are parallel but spaced far apart (the step height), so they
    are grouped by shared span and length, not by perpendicular proximity.
    """
    if a.category != b.category:
        return False
    a_lo, a_hi = _span(a)
    b_lo, b_hi = _span(b)
    overlap = min(a_hi, b_hi) - max(a_lo, b_lo)
    shorter = min(a_hi - a_lo, b_hi - b_lo)
    if shorter <= 0 or overlap < STAIR_SPAN_OVERLAP * shorter:
        return False
    ratio = max(a.length, b.length) / max(1.0, min(a.length, b.length))
    return ratio <= STAIR_LEN_RATIO


def _is_stair_cluster(group: list[LineSegment]) -> bool:
    if len(group) < STAIR_SUCCESSIVE_MIN:
        return False
    coords = sorted(_perpendicular_coord(l) for l in group)
    diffs = [coords[i + 1] - coords[i] for i in range(len(coords) - 1)]
    median = float(np.median(diffs)) if diffs else 0.0
    if median <= 0:
        return False
    return float(np.max(np.abs(np.asarray(diffs) - median))) <= STAIR_SPACING_DEV * median


def remove_stairs(lines: list[LineSegment]) -> list[LineSegment]:
    """Drop the repetitive parallel treads of a staircase (false walls)."""
    if len(lines) < STAIR_SUCCESSIVE_MIN:
        return lines

    to_drop: set[int] = set()
    for cat in (LineCategory.HORIZONTAL, LineCategory.VERTICAL):
        candidates = [l for l in lines if l.category == cat and STAIR_MIN_LEN <= l.length <= STAIR_MAX_LEN]
        groups: list[list[LineSegment]] = []
        for c in candidates:
            placed = False
            for g in groups:
                if _same_stair_family(c, g[0]):
                    g.append(c)
                    placed = True
                    break
            if not placed:
                groups.append([c])
        for g in groups:
            if _is_stair_cluster(g):
                to_drop.update(id(l) for l in g)

    if not to_drop:
        return lines
    return [l for l in lines if id(l) not in to_drop]
