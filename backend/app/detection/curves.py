"""CURVE simplification for curved walls / organic shapes.

HoughLinesP splits a curved wall (arc, ellipse, bay window, organic shape) into
dozens of tiny diagonal chords. We reconnect those chords into a smooth
polyline and simplify it with Douglas–Peucker so the result is a few long,
clean chords that preserve the shape. Straight angled walls are single
segments and are untouched; hatching is already removed by the stairs filter.
"""

from __future__ import annotations

import math
from uuid import uuid4

from app.detection.schemas import LineCategory, LineSegment

# Endpoints within this distance are considered the same vertex.
CONNECT_TOL = 14.0
# A chain needs at least this many segments to be worth simplifying.
MIN_CHAIN = 4
# Douglas-Peucker tolerance (px) for simplification.
DP_EPSILON = 4.0


def _dist(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _endpoints(line: LineSegment) -> tuple[tuple[float, float], tuple[float, float]]:
    return (line.x1, line.y1), (line.x2, line.y2)


def _share_vertex(a: LineSegment, b: LineSegment) -> bool:
    a1, a2 = _endpoints(a)
    b1, b2 = _endpoints(b)
    return any(_dist(p, q) <= CONNECT_TOL for p in (a1, a2) for q in (b1, b2))


def _other_endpoint(line: LineSegment, tip: tuple[float, float]) -> tuple[float, float]:
    e1, e2 = _endpoints(line)
    if _dist(tip, e1) <= CONNECT_TOL:
        return e2
    if _dist(tip, e2) <= CONNECT_TOL:
        return e1
    return e2


def _order_chain(segs: list[LineSegment]) -> list[tuple[float, float]]:
    """Order connected segments into a single polyline of points."""
    segs = list(segs)
    n = len(segs)
    if n == 0:
        return []
    adj: list[set[int]] = [set() for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if _share_vertex(segs[i], segs[j]):
                adj[i].add(j)
                adj[j].add(i)

    # Start at a loose end (lowest degree) so we don't begin mid-chain.
    start = min(range(n), key=lambda i: (len(adj[i]) == 0, len(adj[i])))
    e1, e2 = _endpoints(segs[start])
    # Prefer a start tip NOT shared with any neighbour (a true end).
    shared_e1 = any(
        _dist(e1, q) <= CONNECT_TOL
        for k in adj[start] for q in _endpoints(segs[k])
    )
    shared_e2 = any(
        _dist(e2, q) <= CONNECT_TOL
        for k in adj[start] for q in _endpoints(segs[k])
    )
    tip = e1 if not shared_e1 else e2 if not shared_e2 else e1

    order = [tip]
    used = {start}
    cur = start
    while True:
        nxts = [k for k in adj[cur] if k not in used]
        if not nxts:
            break
        nxt = nxts[0]
        used.add(nxt)
        tip = _other_endpoint(segs[nxt], order[-1])
        order.append(tip)
        cur = nxt
    return order


def _dp(points: list[tuple[float, float]], eps: float) -> list[tuple[float, float]]:
    if len(points) < 3:
        return points

    def perp_distance(p, a, b) -> float:
        ax, ay = a
        bx, by = b
        px, py = p
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy)
        if length == 0:
            return _dist(p, a)
        return abs(dy * px - dx * py + bx * ay - by * ax) / length

    start, end = points[0], points[-1]
    idx = max(range(1, len(points) - 1), key=lambda i: perp_distance(points[i], start, end))
    dmax = perp_distance(points[idx], start, end)
    if dmax > eps:
        left = _dp(points[: idx + 1], eps)
        right = _dp(points[idx:], eps)
        return left[:-1] + right
    return [start, end]


def _to_segments(points: list[tuple[float, float]]) -> list[LineSegment]:
    out: list[LineSegment] = []
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        out.append(LineSegment(
            id=uuid4(), x1=x1, y1=y1, x2=x2, y2=y2,
            angle=round(math.degrees(math.atan2(abs(y2 - y1), x2 - x1)), 2),
            length=round(_dist(points[i], points[i + 1]), 2),
            category=LineCategory.DIAGONAL,
        ))
    return out


def simplify_curves(lines: list[LineSegment]) -> list[LineSegment]:
    """Replace noisy curved polylines with a few clean chords."""
    diags = [ln for ln in lines if ln.category == LineCategory.DIAGONAL]
    if not diags or len(diags) < MIN_CHAIN:
        return lines
    others = [ln for ln in lines if ln.category != LineCategory.DIAGONAL]

    # connected components of the diagonal graph
    n = len(diags)
    parent: list[int] = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            if _share_vertex(diags[i], diags[j]):
                ri, rj = find(i), find(j)
                if ri != rj:
                    parent[rj] = ri

    comps: dict[int, list[int]] = {}
    for idx in range(len(diags)):
        comps.setdefault(find(idx), []).append(idx)

    result: list[LineSegment] = list(others)
    for indices in comps.values():
        if len(indices) < MIN_CHAIN:
            result.extend(diags[i] for i in indices)
            continue
        chain_segs = [diags[i] for i in indices]
        try:
            polyline = _order_chain(chain_segs)
        except Exception:
            result.extend(chain_segs)
            continue
        if len(polyline) < 3:
            result.extend(chain_segs)
            continue
        simplified = _dp(polyline, DP_EPSILON)
        if len(simplified) >= len(chain_segs):
            result.extend(chain_segs)
            continue
        result.extend(_to_segments(simplified))
    return result
