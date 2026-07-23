from __future__ import annotations

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class LineCategory(StrEnum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    DIAGONAL = "diagonal"


class LineSegment(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    x1: float
    y1: float
    x2: float
    y2: float
    angle: float
    length: float
    category: LineCategory


class Intersection(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    x: float
    y: float
    lines: list[UUID]


class LineDetectionResult(BaseModel):
    lines: list[LineSegment]
    horizontal: list[LineSegment] = []
    vertical: list[LineSegment] = []
    diagonal: list[LineSegment] = []
    grouped_lines: list[LineSegment] = []
    intersections: list[Intersection] = []
    image_width: int = 0
    image_height: int = 0


# ── Door detection ──────────────────────────────────────────────────────────


class DoorType(StrEnum):
    SINGLE = "single"
    DOUBLE = "double"
    SLIDING = "sliding"


class DoorArc(BaseModel):
    center_x: float
    center_y: float
    radius: float
    start_angle: float
    end_angle: float


class Door(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: DoorType
    x: float
    y: float
    width: float
    rotation: float
    hinge_x: float
    hinge_y: float
    leaf_length: float = 0.0
    leaf_x1: float = 0.0
    leaf_y1: float = 0.0
    leaf_x2: float = 0.0
    leaf_y2: float = 0.0
    wall_gap_x1: float = 0.0
    wall_gap_y1: float = 0.0
    wall_gap_x2: float = 0.0
    wall_gap_y2: float = 0.0
    swing: str = "right"
    arc: DoorArc | None = None
    confidence: float = 0.0


class DoorDetectionResult(BaseModel):
    doors: list[Door]
    image_width: int = 0
    image_height: int = 0


# ── Window detection ─────────────────────────────────────────────────────────


class WindowType(StrEnum):
    SLIDING = "sliding"      # Corredera
    FIXED = "fixed"           # Fija
    CASEMENT = "casement"     # Batiente


class Orientation(StrEnum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class WindowArc(BaseModel):
    center_x: float
    center_y: float
    radius: float
    start_angle: float
    end_angle: float


class Window(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: WindowType
    x: float
    y: float
    width: float
    height: float
    rotation: float
    orientation: Orientation
    wall_gap_x1: float = 0.0
    wall_gap_y1: float = 0.0
    wall_gap_x2: float = 0.0
    wall_gap_y2: float = 0.0
    glass_lines: int = 0
    arc: WindowArc | None = None
    confidence: float = 0.0


class WindowDetectionResult(BaseModel):
    windows: list[Window]
    image_width: int = 0
    image_height: int = 0
