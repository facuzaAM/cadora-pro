"""Post-detection wall refinement.

The raw grouped lines contain strokes that doors and windows already explain
(door leaves, swing-arc chords, glass lines) plus walls that were chained
through an opening by the collinear merger. This module removes and splits
those lines so the editor and the CAD export only see real wall strokes.
"""

from __future__ import annotations

import math
from uuid import uuid4

from app.detection.schemas import (
    Door,
    LineCategory,
    LineSegment,
    Window,
)

# Perpendicular tolerance when deciding a line is collinear with an opening.
OPENING_TOL = 8.0
# Padding subtracted/added around an opening when splitting a wall.
SPLIT_PAD = 2.0
# Wall fragments shorter than this are dropped after splitting.
MIN_FRAGMENT = 12.0
# Two parallel strokes closer than this are the two sides of one wall.
DUP_DISTANCE = 14.0
# ...and must overlap this much of the shorter span to be merged.
DUP_OVERLAP = 0.75
# Arc-chord endpoints must sit within radius ± this fraction.
ARC_TOL_RATIO = 0.25
ARC_TOL_MIN = 8.0


def refine_walls(
    grouped_lines: list[LineSegment],
    doors: list[Door],
    windows: list[Window],
) -> list[LineSegment]:
    """Drop opening artefacts and split walls at door/window gaps."""
    kept = [
        line for line in grouped_lines
        if not _explained_by_door(line, doors)
        and not _explained_by_window(line, windows)
    ]
    kept = _split_at_openings(kept, doors, windows)
    kept = _merge_parallel_duplicates(kept)
    return kept


# ── explained lines ──────────────────────────────────────────────────────────


def _explained_by_door(line: LineSegment, doors: list[Door]) -> bool:
    for door in doors:
        if _is_door_leaf(line, door):
            return True
        if _is_arc_chord(line, door):
            return True
        if _inside_gap(line, _door_gap(door)):
            return True
    return False


def _explained_by_window(line: LineSegment, windows: list[Window]) -> bool:
    for win in windows:
        gap = (win.wall_gap_x1, win.wall_gap_y1, win.wall_gap_x2, win.wall_gap_y2)
        if _inside_gap(line, gap):
            return True
    return False


def _door_gap(door: Door) -> tuple[float, float, float, float]:
    return (door.wall_gap_x1, door.wall_gap_y1, door.wall_gap_x2, door.wall_gap_y2)


def _is_door_leaf(line: LineSegment, door: Door) -> bool:
    """True when the line is the door's own leaf stroke."""
    leaf_len = math.hypot(
        door.leaf_x2 - door.leaf_x1, door.leaf_y2 - door.leaf_y1,
    )
    if leaf_len < 5 or line.length < 5:
        return False
    if not _nearly_collinear(line, door.leaf_x1, door.leaf_y1, door.leaf_x2, door.leaf_y2):
        return False
    overlap = _span_overlap(
        line.x1, line.y1, line.x2, line.y2,
        door.leaf_x1, door.leaf_y1, door.leaf_x2, door.leaf_y2,
    )
    return overlap >= 0.5 * min(line.length, leaf_len)


def _is_arc_chord(line: LineSegment, door: Door) -> bool:
    """True when both endpoints sit on the door's swing arc.

    Hough approximates the quarter-circle swing arc with short chords; both
    chord endpoints are ~radius away from the hinge, which real walls are not.
    """
    arc = door.arc
    if arc is None or arc.radius < 5:
        return False
    if line.length > 1.5 * arc.radius:
        return False
    tol = max(ARC_TOL_MIN, arc.radius * ARC_TOL_RATIO)
    d1 = math.hypot(line.x1 - arc.center_x, line.y1 - arc.center_y)
    d2 = math.hypot(line.x2 - arc.center_x, line.y2 - arc.center_y)
    return abs(d1 - arc.radius) <= tol and abs(d2 - arc.radius) <= tol


def _inside_gap(
    line: LineSegment, gap: tuple[float, float, float, float],
) -> bool:
    """True when the line lies along an opening gap (glass / sliding track).

    The line must be nearly collinear with the gap and its span mostly
    contained in the gap span; walls flanking the opening have no overlap.
    """
    gx1, gy1, gx2, gy2 = gap
    gap_len = math.hypot(gx2 - gx1, gy2 - gy1)
    if gap_len < 5 or line.length < 5:
        return False
    if not _nearly_collinear(line, gx1, gy1, gx2, gy2):
        return False
    overlap = _span_overlap(
        line.x1, line.y1, line.x2, line.y2, gx1, gy1, gx2, gy2,
    )
    return overlap >= 0.6 * line.length


def _nearly_collinear(
    line: LineSegment, x1: float, y1: float, x2: float, y2: float,
) -> bool:
    """Direction matches (within ~18deg) and the line sits close to the segment."""
    la = math.hypot(line.x2 - line.x1, line.y2 - line.y1)
    lb = math.hypot(x2 - x1, y2 - y1)
    if la == 0 or lb == 0:
        return False
    ua = ((line.x2 - line.x1) / la, (line.y2 - line.y1) / la)
    ub = ((x2 - x1) / lb, (y2 - y1) / lb)
    if abs(ua[0] * ub[0] + ua[1] * ub[1]) < 0.95:
        return False
    dist1 = abs(ua[1] * (x1 - line.x1) - ua[0] * (y1 - line.y1))
    dist2 = abs(ua[1] * (x2 - line.x1) - ua[0] * (y2 - line.y1))
    return min(dist1, dist2) <= OPENING_TOL


def _span_overlap(
    ax1: float, ay1: float, ax2: float, ay2: float,
    bx1: float, by1: float, bx2: float, by2: float,
) -> float:
    """Overlap of the two segments projected on the first segment's axis."""
    la = math.hypot(ax2 - ax1, ay2 - ay1)
    if la == 0:
        return 0.0
    ua = ((ax2 - ax1) / la, (ay2 - ay1) / la)
    a1, a2 = 0.0, la
    b1 = (bx1 - ax1) * ua[0] + (by1 - ay1) * ua[1]
    b2 = (bx2 - ax1) * ua[0] + (by2 - ay1) * ua[1]
    return max(0.0, min(a2, max(b1, b2)) - max(a1, min(b1, b2)))


# ── splitting at openings ────────────────────────────────────────────────────


def _split_at_openings(
    lines: list[LineSegment], doors: list[Door], windows: list[Window],
) -> list[LineSegment]:
    gaps: list[tuple[float, float, float, float]] = [_door_gap(d) for d in doors]
    gaps += [
        (w.wall_gap_x1, w.wall_gap_y1, w.wall_gap_x2, w.wall_gap_y2)
        for w in windows
    ]

    result: list[LineSegment] = []
    for line in lines:
        if line.category == LineCategory.DIAGONAL:
            result.append(line)
            continue
        cuts = [
            _gap_interval(gap) for gap in gaps
            if _gap_on_line(line, gap)
        ]
        result.extend(_cut_line(line, cuts))
    return result


def _gap_interval(
    gap: tuple[float, float, float, float],
) -> tuple[float, float]:
    gx1, gy1, gx2, gy2 = gap
    if abs(gx2 - gx1) >= abs(gy2 - gy1):
        return (min(gx1, gx2), max(gx1, gx2))
    return (min(gy1, gy2), max(gy1, gy2))


def _gap_on_line(
    line: LineSegment, gap: tuple[float, float, float, float],
) -> bool:
    """True when the gap is cut into this wall (same axis, same position)."""
    gx1, gy1, gx2, gy2 = gap
    gap_horizontal = abs(gx2 - gx1) >= abs(gy2 - gy1)
    if line.category == LineCategory.HORIZONTAL:
        if not gap_horizontal:
            return False
        line_y = (line.y1 + line.y2) / 2.0
        gap_y = (gy1 + gy2) / 2.0
        if abs(line_y - gap_y) > OPENING_TOL:
            return False
        lo, hi = min(line.x1, line.x2), max(line.x1, line.x2)
        glo, ghi = _gap_interval(gap)
        return min(hi, ghi) - max(lo, glo) > 0
    if line.category == LineCategory.VERTICAL:
        if gap_horizontal:
            return False
        line_x = (line.x1 + line.x2) / 2.0
        gap_x = (gx1 + gx2) / 2.0
        if abs(line_x - gap_x) > OPENING_TOL:
            return False
        lo, hi = min(line.y1, line.y2), max(line.y1, line.y2)
        glo, ghi = _gap_interval(gap)
        return min(hi, ghi) - max(lo, glo) > 0
    return False


def _cut_line(
    line: LineSegment, cuts: list[tuple[float, float]],
) -> list[LineSegment]:
    """Split an axis-aligned line by removing the cut intervals."""
    if line.category == LineCategory.HORIZONTAL:
        lo, hi = min(line.x1, line.x2), max(line.x1, line.x2)
        y = (line.y1 + line.y2) / 2.0
        spans = _subtract(lo, hi, cuts)
        return [
            LineSegment(
                id=uuid4(), x1=s, y1=y, x2=e, y2=y,
                angle=0.0, length=e - s, category=LineCategory.HORIZONTAL,
            )
            for s, e in spans
        ]
    lo, hi = min(line.y1, line.y2), max(line.y1, line.y2)
    x = (line.x1 + line.x2) / 2.0
    spans = _subtract(lo, hi, cuts)
    return [
        LineSegment(
            id=uuid4(), x1=x, y1=s, x2=x, y2=e,
            angle=90.0, length=e - s, category=LineCategory.VERTICAL,
        )
        for s, e in spans
    ]


def _subtract(
    lo: float, hi: float, cuts: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    ordered = sorted((max(c - SPLIT_PAD, lo), min(e + SPLIT_PAD, hi)) for c, e in cuts)
    spans: list[tuple[float, float]] = []
    cursor = lo
    for cut_lo, cut_hi in ordered:
        if cut_lo > cursor and cut_lo - cursor >= MIN_FRAGMENT:
            spans.append((cursor, cut_lo))
        cursor = max(cursor, cut_hi)
    if hi - cursor >= MIN_FRAGMENT:
        spans.append((cursor, hi))
    return spans


# ── duplicate parallel strokes ───────────────────────────────────────────────


def _merge_parallel_duplicates(lines: list[LineSegment]) -> list[LineSegment]:
    """Merge the two strokes of a double-line wall into one centreline.

    Only pairs that are very close and overlap almost completely are merged,
    so distinct parallel walls (or furniture) are never collapsed.
    """
    parent = list(range(len(lines)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            if _are_parallel_duplicates(lines[i], lines[j]):
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[rj] = ri

    groups: dict[int, list[LineSegment]] = {}
    for idx, line in enumerate(lines):
        groups.setdefault(find(idx), []).append(line)

    result: list[LineSegment] = []
    for group in groups.values():
        if len(group) == 1:
            result.append(group[0])
            continue
        result.append(_merge_parallel_group(group))
    return result


def _are_parallel_duplicates(a: LineSegment, b: LineSegment) -> bool:
    if a.category != b.category or a.category == LineCategory.DIAGONAL:
        return False
    if a.category == LineCategory.HORIZONTAL:
        if abs((a.y1 + a.y2) / 2.0 - (b.y1 + b.y2) / 2.0) > DUP_DISTANCE:
            return False
        a_lo, a_hi = min(a.x1, a.x2), max(a.x1, a.x2)
        b_lo, b_hi = min(b.x1, b.x2), max(b.x1, b.x2)
    else:
        if abs((a.x1 + a.x2) / 2.0 - (b.x1 + b.x2) / 2.0) > DUP_DISTANCE:
            return False
        a_lo, a_hi = min(a.y1, a.y2), max(a.y1, a.y2)
        b_lo, b_hi = min(b.y1, b.y2), max(b.y1, b.y2)
    overlap = min(a_hi, b_hi) - max(a_lo, b_lo)
    shorter = min(a_hi - a_lo, b_hi - b_lo)
    return shorter > 0 and overlap >= DUP_OVERLAP * shorter


def _merge_parallel_group(group: list[LineSegment]) -> LineSegment:
    cat = group[0].category
    if cat == LineCategory.HORIZONTAL:
        y = sum((seg.y1 + seg.y2) / 2.0 for seg in group) / len(group)
        xs = [p for seg in group for p in (seg.x1, seg.x2)]
        return LineSegment(
            id=uuid4(), x1=min(xs), y1=y, x2=max(xs), y2=y,
            angle=0.0, length=max(xs) - min(xs), category=cat,
        )
    x = sum((seg.x1 + seg.x2) / 2.0 for seg in group) / len(group)
    ys = [p for seg in group for p in (seg.y1, seg.y2)]
    return LineSegment(
        id=uuid4(), x1=x, y1=min(ys), x2=x, y2=max(ys),
        angle=90.0, length=max(ys) - min(ys), category=cat,
    )
