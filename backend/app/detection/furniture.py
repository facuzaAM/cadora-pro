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

from app.detection.schemas import LineSegment

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
