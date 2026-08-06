from __future__ import annotations

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class WallElement(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    x1: float
    y1: float
    x2: float
    y2: float


class DoorElementType(StrEnum):
    SINGLE = "single"
    DOUBLE = "double"
    SLIDING = "sliding"


class DoorElement(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: DoorElementType = DoorElementType.SINGLE
    x: float
    y: float
    width: float = Field(gt=0)
    rotation: float = 0.0
    swing: str = "right"


class WindowElementType(StrEnum):
    SLIDING = "sliding"
    FIXED = "fixed"
    CASEMENT = "casement"


class WindowElement(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: WindowElementType = WindowElementType.SLIDING
    x: float
    y: float
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    rotation: float = 0.0


class ElementsPayload(BaseModel):
    walls: list[WallElement] = []
    doors: list[DoorElement] = []
    windows: list[WindowElement] = []
