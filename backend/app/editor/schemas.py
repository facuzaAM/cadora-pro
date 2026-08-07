from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.detection.schemas import DoorType, WindowType


class WallElement(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    x1: float
    y1: float
    x2: float
    y2: float


class DoorElement(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: DoorType = DoorType.SINGLE
    x: float
    y: float
    width: float = Field(gt=0)
    rotation: float = 0.0
    swing: str = "right"


class WindowElement(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: WindowType = WindowType.SLIDING
    x: float
    y: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    rotation: float = 0.0


class ElementsPayload(BaseModel):
    walls: list[WallElement] = []
    doors: list[DoorElement] = []
    windows: list[WindowElement] = []
