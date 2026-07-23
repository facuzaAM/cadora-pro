from __future__ import annotations

from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TextCategory(StrEnum):
    MEASUREMENT = "measurement"
    ROOM_NAME = "room_name"
    SCALE = "scale"
    NOTE = "note"
    UNKNOWN = "unknown"


class OcrTextElement(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    text: str
    category: TextCategory
    confidence: float
    bbox: tuple[float, float, float, float]  # x_min, y_min, x_max, y_max
    font_size: float | None = None
    rotation: float = 0.0


class OcrResult(BaseModel):
    texts: list[OcrTextElement]
    measurements: list[OcrTextElement] = []
    room_names: list[OcrTextElement] = []
    scales: list[OcrTextElement] = []
    notes: list[OcrTextElement] = []
    raw_text: str = ""
    page_count: int = 1


class OcrRequest(BaseModel):
    detect_measurements: bool = True
    detect_room_names: bool = True
    detect_scales: bool = True
    detect_notes: bool = True
    language: str = "spa+eng"
