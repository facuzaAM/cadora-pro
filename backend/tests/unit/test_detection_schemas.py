from app.detection.schemas import (
    Door,
    DoorType,
    LineCategory,
    LineSegment,
    Orientation,
    Window,
    WindowType,
)


def test_line_categories():
    assert LineCategory.HORIZONTAL.value == "horizontal"
    assert LineCategory.VERTICAL.value == "vertical"
    assert LineCategory.DIAGONAL.value == "diagonal"


def test_door_types():
    assert DoorType.SINGLE.value == "single"
    assert DoorType.DOUBLE.value == "double"
    assert DoorType.SLIDING.value == "sliding"


def test_window_types():
    assert WindowType.SLIDING.value == "sliding"
    assert WindowType.FIXED.value == "fixed"
    assert WindowType.CASEMENT.value == "casement"


def test_line_segment():
    seg = LineSegment(
        x1=10.0,
        y1=20.0,
        x2=100.0,
        y2=20.0,
        angle=0.0,
        length=90.0,
        category=LineCategory.HORIZONTAL,
    )
    assert seg.x1 == 10.0
    assert seg.category == LineCategory.HORIZONTAL
    assert seg.id is not None


def test_door():
    door = Door(
        type=DoorType.SINGLE,
        x=50.0,
        y=50.0,
        width=900.0,
        rotation=0.0,
        hinge_x=50.0,
        hinge_y=50.0,
        confidence=0.88,
    )
    assert door.width == 900.0
    assert door.type == DoorType.SINGLE
    assert door.id is not None


def test_window():
    win = Window(
        type=WindowType.SLIDING,
        x=100.0,
        y=200.0,
        width=1200.0,
        height=1200.0,
        rotation=0.0,
        orientation=Orientation.HORIZONTAL,
        glass_lines=2,
        confidence=0.92,
    )
    assert win.type == WindowType.SLIDING
    assert win.orientation == Orientation.HORIZONTAL
    assert win.glass_lines == 2
    assert win.id is not None
