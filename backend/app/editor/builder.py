from __future__ import annotations

import math

from app.detection.schemas import (
    Door,
    DoorArc,
    DoorDetectionResult,
    DoorType,
    LineCategory,
    LineDetectionResult,
    LineSegment,
    Orientation,
    Window,
    WindowDetectionResult,
    WindowType,
)
from app.editor.schemas import DoorElement, ElementsPayload, WallElement, WindowElement

_ANGLE_TOLERANCE = 8.0


def _line_angle(x1: float, y1: float, x2: float, y2: float) -> float:
    angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
    if angle < 0:
        angle += 180
    return angle


def _classify_angle(angle: float) -> LineCategory:
    if angle <= _ANGLE_TOLERANCE or angle >= 180 - _ANGLE_TOLERANCE:
        return LineCategory.HORIZONTAL
    if 90 - _ANGLE_TOLERANCE <= angle <= 90 + _ANGLE_TOLERANCE:
        return LineCategory.VERTICAL
    return LineCategory.DIAGONAL


def _snap_axis(rotation: float) -> float:
    """Snap a rotation to the nearest axis-aligned direction (0 / 90)."""
    normalized = rotation % 180
    if normalized < 0:
        normalized += 180
    return 0.0 if normalized <= 45 or normalized >= 135 else 90.0


# ── Walls ────────────────────────────────────────────────────────────────────


def _build_line(wall: WallElement) -> LineSegment:
    angle = _line_angle(wall.x1, wall.y1, wall.x2, wall.y2)
    length = math.hypot(wall.x2 - wall.x1, wall.y2 - wall.y1)
    return LineSegment(
        id=wall.id,
        x1=wall.x1,
        y1=wall.y1,
        x2=wall.x2,
        y2=wall.y2,
        angle=round(angle, 2),
        length=length,
        category=_classify_angle(angle),
    )


def build_walls(walls: list[WallElement]) -> LineDetectionResult:
    segments = [_build_line(w) for w in walls]
    return LineDetectionResult(
        lines=segments,
        horizontal=[s for s in segments if s.category == LineCategory.HORIZONTAL],
        vertical=[s for s in segments if s.category == LineCategory.VERTICAL],
        diagonal=[s for s in segments if s.category == LineCategory.DIAGONAL],
        grouped_lines=segments,
        intersections=[],
    )


# ── Doors ────────────────────────────────────────────────────────────────────


def _build_door(door: DoorElement) -> Door:
    rad = math.radians(door.rotation)
    gap_dx = math.cos(rad)
    gap_dy = math.sin(rad)
    half = door.width / 2.0

    hinge_x = door.x - half * gap_dx
    hinge_y = door.y - half * gap_dy
    gap_x2 = door.x + half * gap_dx
    gap_y2 = door.y + half * gap_dy

    perp_x = -gap_dy
    perp_y = gap_dx
    if door.swing != "right":
        perp_x = -perp_x
        perp_y = -perp_y

    is_sliding = door.type == DoorType.SLIDING

    if is_sliding:
        return Door(
            id=door.id,
            type=door.type,
            x=door.x,
            y=door.y,
            width=door.width,
            rotation=door.rotation,
            hinge_x=hinge_x,
            hinge_y=hinge_y,
            leaf_x1=hinge_x,
            leaf_y1=hinge_y,
            leaf_x2=hinge_x,
            leaf_y2=hinge_y,
            wall_gap_x1=hinge_x,
            wall_gap_y1=hinge_y,
            wall_gap_x2=gap_x2,
            wall_gap_y2=gap_y2,
            swing=door.swing,
            arc=None,
        )

    leaf_x1 = hinge_x + door.width * perp_x
    leaf_y1 = hinge_y + door.width * perp_y

    base_angle = door.rotation % 360
    if door.swing == "right":
        start_angle = base_angle
        end_angle = base_angle + 90
    else:
        start_angle = base_angle - 90
        end_angle = base_angle

    arc = DoorArc(
        center_x=hinge_x,
        center_y=hinge_y,
        radius=door.width,
        start_angle=start_angle,
        end_angle=end_angle,
    )

    return Door(
        id=door.id,
        type=door.type,
        x=door.x,
        y=door.y,
        width=door.width,
        rotation=door.rotation,
        hinge_x=hinge_x,
        hinge_y=hinge_y,
        leaf_length=door.width,
        leaf_x1=leaf_x1,
        leaf_y1=leaf_y1,
        leaf_x2=door.x,
        leaf_y2=door.y,
        wall_gap_x1=hinge_x,
        wall_gap_y1=hinge_y,
        wall_gap_x2=gap_x2,
        wall_gap_y2=gap_y2,
        swing=door.swing,
        arc=arc,
    )


def build_doors(doors: list[DoorElement]) -> DoorDetectionResult:
    return DoorDetectionResult(doors=[_build_door(d) for d in doors])


# ── Windows ──────────────────────────────────────────────────────────────────


def _build_window(win: WindowElement) -> Window:
    rot = _snap_axis(win.rotation)
    half = win.width / 2.0

    if rot == 0.0:
        orientation = Orientation.HORIZONTAL
        gap_x1 = win.x - half
        gap_x2 = win.x + half
        gap_y1 = win.y
        gap_y2 = win.y
    else:
        orientation = Orientation.VERTICAL
        gap_x1 = win.x
        gap_x2 = win.x
        gap_y1 = win.y - half
        gap_y2 = win.y + half

    return Window(
        id=win.id,
        type=win.type,
        x=win.x,
        y=win.y,
        width=win.width,
        height=win.height,
        rotation=rot,
        orientation=orientation,
        wall_gap_x1=gap_x1,
        wall_gap_y1=gap_y1,
        wall_gap_x2=gap_x2,
        wall_gap_y2=gap_y2,
        glass_lines=1 if win.type == WindowType.SLIDING else 0,
        arc=None,
    )


def build_windows(windows: list[WindowElement]) -> WindowDetectionResult:
    return WindowDetectionResult(windows=[_build_window(w) for w in windows])


# ── Combined ─────────────────────────────────────────────────────────────────


def build_detection_results(
    elements: ElementsPayload,
    image_width: int = 0,
    image_height: int = 0,
) -> tuple[LineDetectionResult, DoorDetectionResult, WindowDetectionResult]:
    lines = build_walls(elements.walls)
    doors = build_doors(elements.doors)
    windows = build_windows(elements.windows)

    lines.image_width = image_width
    lines.image_height = image_height
    doors.image_width = image_width
    doors.image_height = image_height
    windows.image_width = image_width
    windows.image_height = image_height
    return lines, doors, windows
