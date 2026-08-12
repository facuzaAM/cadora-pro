from __future__ import annotations

from app.detection.refine import refine_walls
from app.detection.schemas import (
    Door,
    DoorArc,
    DoorType,
    LineCategory,
    LineSegment,
    Orientation,
    Window,
    WindowType,
)


def _line(
    x1: float, y1: float, x2: float, y2: float,
    category: LineCategory | None = None,
) -> LineSegment:
    if category is None:
        if abs(y2 - y1) <= abs(x2 - x1):
            category = LineCategory.HORIZONTAL
        else:
            category = LineCategory.VERTICAL
    return LineSegment(
        x1=x1, y1=y1, x2=x2, y2=y2,
        angle=0.0 if category == LineCategory.HORIZONTAL else 90.0,
        length=abs(x2 - x1) + abs(y2 - y1),
        category=category,
    )


def _door(
    gap_x1: float, gap_y1: float, gap_x2: float, gap_y2: float,
    leaf: tuple[float, float, float, float] | None = None,
    arc: DoorArc | None = None,
) -> Door:
    if leaf is None:
        leaf = (gap_x1, gap_y1, gap_x1, gap_y1)
    return Door(
        type=DoorType.SINGLE,
        x=(gap_x1 + gap_x2) / 2, y=(gap_y1 + gap_y2) / 2,
        width=abs(gap_x2 - gap_x1) + abs(gap_y2 - gap_y1),
        rotation=0.0,
        hinge_x=gap_x1, hinge_y=gap_y1,
        leaf_length=abs(leaf[2] - leaf[0]) + abs(leaf[3] - leaf[1]),
        leaf_x1=leaf[0], leaf_y1=leaf[1], leaf_x2=leaf[2], leaf_y2=leaf[3],
        wall_gap_x1=gap_x1, wall_gap_y1=gap_y1,
        wall_gap_x2=gap_x2, wall_gap_y2=gap_y2,
        arc=arc,
        confidence=0.7,
    )


def _window(
    gap_x1: float, gap_y1: float, gap_x2: float, gap_y2: float,
) -> Window:
    horizontal = abs(gap_x2 - gap_x1) >= abs(gap_y2 - gap_y1)
    return Window(
        type=WindowType.SLIDING,
        x=(gap_x1 + gap_x2) / 2, y=(gap_y1 + gap_y2) / 2,
        width=abs(gap_x2 - gap_x1), height=abs(gap_y2 - gap_y1),
        rotation=0.0,
        orientation=Orientation.HORIZONTAL if horizontal else Orientation.VERTICAL,
        wall_gap_x1=gap_x1, wall_gap_y1=gap_y1,
        wall_gap_x2=gap_x2, wall_gap_y2=gap_y2,
        confidence=0.7,
    )


class TestExplainedLines:
    def test_drops_door_leaf_stroke(self):
        leaf = _line(200, 200, 200, 280)
        door = _door(200, 200, 280, 200, leaf=(200, 200, 200, 280))
        result = refine_walls([leaf], [door], [])
        assert result == []

    def test_keeps_wall_perpendicular_to_leaf(self):
        wall = _line(200, 200, 200, 400)
        door = _door(200, 200, 280, 200, leaf=(200, 200, 280, 200))
        result = refine_walls([wall], [door], [])
        assert len(result) >= 1

    def test_drops_arc_chord(self):
        arc = DoorArc(
            center_x=200, center_y=200, radius=80,
            start_angle=0.0, end_angle=90.0,
        )
        chord = _line(280, 200, 270, 240, category=LineCategory.DIAGONAL)
        door = _door(200, 200, 280, 200, arc=arc)
        result = refine_walls([chord], [door], [])
        assert result == []

    def test_keeps_wall_not_on_arc(self):
        arc = DoorArc(
            center_x=200, center_y=200, radius=80,
            start_angle=0.0, end_angle=90.0,
        )
        wall = _line(200, 200, 200, 500)
        door = _door(200, 200, 280, 200, arc=arc)
        result = refine_walls([wall], [door], [])
        assert len(result) >= 1

    def test_drops_glass_line_inside_window_gap(self):
        glass = _line(310, 100, 490, 100)
        window = _window(300, 100, 500, 100)
        result = refine_walls([glass], [], [window])
        assert result == []

    def test_drops_line_inside_door_gap(self):
        track = _line(205, 100, 275, 100)
        door = _door(200, 100, 280, 100)
        result = refine_walls([track], [door], [])
        assert result == []


class TestSplitAtOpenings:
    def test_splits_wall_through_door_gap(self):
        wall = _line(0, 100, 600, 100)
        door = _door(200, 100, 280, 100)
        result = refine_walls([wall], [door], [])
        assert len(result) == 2
        left, right = sorted(result, key=lambda seg: seg.x1)
        assert left.x1 == 0
        assert left.x2 <= 200
        assert right.x2 == 600
        assert right.x1 >= 280

    def test_splits_wall_through_window_gap(self):
        wall = _line(0, 100, 600, 100)
        window = _window(300, 100, 500, 100)
        result = refine_walls([wall], [], [window])
        assert len(result) == 2

    def test_does_not_split_flanking_wall(self):
        wall = _line(0, 100, 150, 100)
        door = _door(200, 100, 280, 100)
        result = refine_walls([wall], [door], [])
        assert len(result) == 1
        assert result[0].x1 == 0 and result[0].x2 == 150

    def test_does_not_split_parallel_wall_on_other_row(self):
        wall = _line(0, 300, 600, 300)
        door = _door(200, 100, 280, 100)
        result = refine_walls([wall], [door], [])
        assert len(result) == 1

    def test_splits_vertical_wall(self):
        wall = _line(100, 0, 100, 600)
        window = _window(100, 250, 100, 350)
        result = refine_walls([wall], [], [window])
        assert len(result) == 2
        top, bottom = sorted(result, key=lambda seg: seg.y1)
        assert top.y1 == 0
        assert bottom.y2 == 600

    def test_drops_tiny_fragments_after_split(self):
        wall = _line(195, 100, 600, 100)
        door = _door(200, 100, 280, 100)
        result = refine_walls([wall], [door], [])
        assert len(result) == 1
        assert result[0].x1 >= 280

    def test_diagonal_lines_pass_through(self):
        diag = _line(0, 0, 300, 300, category=LineCategory.DIAGONAL)
        door = _door(100, 100, 200, 100)
        result = refine_walls([diag], [door], [])
        assert len(result) == 1
        assert result[0] is diag


class TestParallelDuplicates:
    def test_merges_double_line_wall_into_centreline(self):
        a = _line(0, 98, 500, 98)
        b = _line(0, 104, 500, 104)
        result = refine_walls([a, b], [], [])
        assert len(result) == 1
        merged = result[0]
        assert merged.y1 == 101 and merged.y2 == 101
        assert merged.x1 == 0 and merged.x2 == 500

    def test_keeps_distinct_parallel_walls(self):
        a = _line(0, 100, 500, 100)
        b = _line(0, 250, 500, 250)
        result = refine_walls([a, b], [], [])
        assert len(result) == 2

    def test_keeps_barely_overlapping_strokes_separate(self):
        a = _line(0, 100, 500, 100)
        b = _line(400, 105, 900, 105)
        result = refine_walls([a, b], [], [])
        assert len(result) == 2


class TestEndToEnd:
    def test_no_openings_returns_lines_unchanged(self):
        walls = [_line(0, 100, 600, 100), _line(100, 0, 100, 400)]
        result = refine_walls(walls, [], [])
        assert len(result) == 2
