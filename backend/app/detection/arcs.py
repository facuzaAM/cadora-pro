"""Robust arc / curved-wall detection by circle fitting (RANSAC).

RANSAC's line-chords from Hough don't connect reliably, so instead of chaining
them we fit a circle to the CHORD ENDPOINTS: a curved wall is made of many
short chords whose endpoints all lie on the true circle. We take the most
supported circle, keep its inlier endpoints, and emit one `Arc` that replaces
the chord wall. Straight angled walls (single long diagonals) never reach the
inlier threshold and are left untouched.
"""

from __future__ import annotations

import math
import random

from app.detection.schemas import Arc, LineCategory, LineSegment

# A circle needs at least this many distinct inlier endpoints to be an arc.
MIN_INLIERS = 6
# Endpoint-to-circle distance accepted (px).
FIT_TOLERANCE = 6.0
# Circle radius bounds (px).
MIN_RADIUS = 25.0
MAX_RADIUS = 2500.0
RANSAC_ITERATIONS = 500
# Arcs narrower than this (deg) are rejected (too close to a straight line).
MIN_ARC_SPAN = 15.0


def _circle_from_3(p1, p2, p3):
    """Circle (cx, cy, r) through three points, or None."""
    ax, ay = p1
    bx, by = p2
    cx, cy = p3
    d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(d) < 1e-9:
        return None
    ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay)
          + (cx * cx + cy * cy) * (ay - by)) / d
    uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx)
          + (cx * cx + cy * cy) * (bx - ax)) / d
    r = math.hypot(ux - ax, uy - ay)
    return ux, uy, r


def _best_circle(points: list[tuple[float, float]]):
    """RANSAC circle using three-point samples."""
    n = len(points)
    if n < MIN_INLIERS:
        return None
    rng = random.Random(0)  # deterministic for reproducibility
    best = None
    for _ in range(RANSAC_ITERATIONS):
        i, j, k = rng.sample(range(n), 3)
        c = _circle_from_3(points[i], points[j], points[k])
        if c is None:
            continue
        cx, cy, r = c
        if r < MIN_RADIUS or r > MAX_RADIUS:
            continue
        inliers = [
            p for p in points
            if abs(math.hypot(p[0] - cx, p[1] - cy) - r) <= FIT_TOLERANCE
        ]
        if len(inliers) >= MIN_INLIERS and (best is None or len(inliers) > best[0]):
            best = (len(inliers), (cx, cy, r), inliers)
    return best


def _dominant_arc(center, radius, points) -> tuple[float, float] | None:
    """Start/end angles (deg CCW) spanning the arc of the inlier points."""
    cx, cy = center
    angles = [
        (math.degrees(math.atan2(p[1] - cy, p[0] - cx)) % 360) for p in points
    ]
    angles = sorted(set(round(a, 2) for a in angles))
    if len(angles) < 2:
        return None
    n = len(angles)
    gaps = [(angles[(i + 1) % n] - angles[i]) % 360 for i in range(n)]
    gi = gaps.index(max(gaps))
    start = angles[(gi + 1) % n]
    end = angles[gi]
    if end <= start:
        end += 360
    span = end - start
    if span < MIN_ARC_SPAN:
        return None
    return start, end


def _on_arc(p, arc: Arc) -> bool:
    return abs(math.hypot(p[0] - arc.center_x, p[1] - arc.center_y)
               - arc.radius) <= FIT_TOLERANCE


def _endpoints_in_arc(line: LineSegment, arc: Arc) -> bool:
    return _on_arc((line.x1, line.y1), arc) and _on_arc((line.x2, line.y2), arc)


def detect_arcs(lines: list[LineSegment]) -> tuple[list[Arc], list[LineSegment]]:
    """Return (arcs, kept_lines); a curved wall's chords are replaced by an Arc."""
    if not lines:
        return [], lines

    points = [
        (ln.x1, ln.y1) for ln in lines if ln.category == LineCategory.DIAGONAL
    ] + [
        (ln.x2, ln.y2) for ln in lines if ln.category == LineCategory.DIAGONAL
    ]
    arcs: list[Arc] = []
    remaining = list(lines)
    consumed: set[int] = set()

    # Avoid re-fitting the same points forever: cap the number of arcs.
    for _ in range(8):
        best = _best_circle(points)
        if best is None:
            break
        _, (cx, cy, r), inliers = best
        extent = _dominant_arc((cx, cy), r, inliers)
        if extent is None:
            break
        start_deg, end_deg = extent
        arc = Arc(
            center_x=cx, center_y=cy, radius=r,
            start_angle=start_deg, end_angle=end_deg,
        )
        arcs.append(arc)

        # Consume the diagonal strokes that lie on this arc.
        newly = {
            id(ln) for ln in remaining
            if ln.category == LineCategory.DIAGONAL and _endpoints_in_arc(ln, arc)
        }
        if not newly:
            break
        consumed |= newly
        remaining = [ln for ln in remaining if id(ln) not in consumed]

        # Drop all inlier points from the pool so we can find another arc.
        inlier_set = {
            (round(x, 1), round(y, 1)) for x, y in inliers
        }
        points = [
            (x, y) for (x, y) in points
            if (round(x, 1), round(y, 1)) not in inlier_set
        ]
        if len(points) < MIN_INLIERS:
            break

    return arcs, remaining
