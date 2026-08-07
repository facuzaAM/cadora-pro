from uuid import uuid4

from app.detection.schemas import LineCategory, Orientation
from app.editor.builder import (
    _snap_axis,
    build_detection_results,
    build_doors,
    build_walls,
    build_windows,
)
from app.editor.schemas import (
    DoorElement,
    ElementsPayload,
    WallElement,
    WindowElement,
)


def test_build_walls_categorize_lines():
    result = build_walls(
        [
            WallElement(id=uuid4(), x1=0, y1=0, x2=100, y2=0),
            WallElement(id=uuid4(), x1=10, y1=0, x2=10, y2=80),
            WallElement(id=uuid4(), x1=0, y1=0, x2=50, y2=50),
        ]
    )
    categories = [s.category for s in result.grouped_lines]
    assert LineCategory.HORIZONTAL in categories
    assert LineCategory.VERTICAL in categories
    assert LineCategory.DIAGONAL in categories
    assert len(result.lines) == 3
    assert result.grouped_lines == result.lines
    assert result.horizontal[0].angle == 0.0


def test_build_wall_length_and_angle():
    line = build_walls(
        [WallElement(id=uuid4(), x1=0, y1=0, x2=30, y2=40)]
    ).grouped_lines[0]
    assert line.length == 50.0
    assert round(line.angle, 2) == round(53.13, 2)


def test_build_door_right_swing():
    doors = build_doors(
        [
            DoorElement(
                id=uuid4(), x=50, y=0, width=20, rotation=0, swing="right",
            )
        ]
    )
    door = doors.doors[0]
    assert door.hinge_x == 40.0
    assert door.hinge_y == 0.0
    assert door.wall_gap_x2 == 60.0
    assert door.leaf_x1 == 40.0
    assert door.leaf_y1 == 20.0
    assert door.arc is not None
    assert door.arc.radius == 20.0
    assert door.arc.start_angle == 0.0
    assert door.arc.end_angle == 90.0


def test_build_door_left_swing():
    door = build_doors(
        [DoorElement(id=uuid4(), x=0, y=0, width=10, rotation=0, swing="left")]
    ).doors[0]
    assert door.leaf_y1 == -10.0
    assert door.arc is not None
    assert door.arc.start_angle == -90.0
    assert door.arc.end_angle == 0.0


def test_build_door_sliding_no_arc():
    door = build_doors(
        [
            DoorElement(
                id=uuid4(), x=0, y=0, width=12, rotation=0, type="sliding",
            )
        ]
    ).doors[0]
    assert door.arc is None
    assert door.leaf_length == 0.0


def test_build_windows_horizontal():
    win = build_windows(
        [WindowElement(id=uuid4(), x=80, y=0, width=30, height=5, rotation=0)]
    ).windows[0]
    assert win.orientation == Orientation.HORIZONTAL
    assert win.wall_gap_x1 == 65.0
    assert win.wall_gap_x2 == 95.0
    assert win.wall_gap_y1 == 0.0
    assert win.height == 5.0


def test_build_windows_vertical():
    win = build_windows(
        [WindowElement(id=uuid4(), x=0, y=50, width=30, height=5, rotation=90)]
    ).windows[0]
    assert win.orientation == Orientation.VERTICAL
    assert win.wall_gap_y1 == 35.0
    assert win.wall_gap_y2 == 65.0
    assert win.wall_gap_x1 == 0.0


def test_snap_axis():
    assert _snap_axis(0) == 0.0
    assert _snap_axis(89) == 90.0
    assert _snap_axis(90) == 90.0
    assert _snap_axis(270) == 90.0
    assert _snap_axis(180) == 0.0
    assert _snap_axis(45) == 0.0


def test_build_detection_results_sets_dims():
    lines, doors, windows = build_detection_results(
        ElementsPayload(
            walls=[WallElement(id=uuid4(), x1=0, y1=0, x2=100, y2=0)],
            doors=[DoorElement(id=uuid4(), x=50, y=0, width=20, rotation=0)],
            windows=[WindowElement(id=uuid4(), x=80, y=0, width=30, height=5, rotation=0)],
        ),
        image_width=800,
        image_height=600,
    )
    assert lines.image_width == 800
    assert lines.image_height == 600
    assert doors.image_width == 800
    assert windows.image_height == 600
