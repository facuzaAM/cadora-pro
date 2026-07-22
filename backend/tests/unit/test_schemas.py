from app.detection.schemas import Orientation


def test_orientation_values():
    assert Orientation.HORIZONTAL.value == "horizontal"
    assert Orientation.VERTICAL.value == "vertical"


def test_orientation_members():
    assert len(Orientation) == 2
    assert Orientation.HORIZONTAL in Orientation
    assert Orientation.VERTICAL in Orientation
