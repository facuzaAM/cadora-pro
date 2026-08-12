"""Tests for detection quality metrics computed at serialization time."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.detection.pipeline import serialize_detection  # noqa: E402
from app.detection.schemas import (  # noqa: E402
    Door,
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
from app.ocr.schemas import OcrResult  # noqa: E402


def _wall(x: int) -> LineSegment:
    return LineSegment(
        x1=x, y1=0, x2=x + 100, y2=0, angle=0, length=100,
        category=LineCategory.HORIZONTAL,
    )


def test_quality_metrics_persisted() -> None:
    lines = LineDetectionResult(lines=[], grouped_lines=[_wall(0), _wall(200)])
    doors = DoorDetectionResult(doors=[
        Door(type=DoorType.SINGLE, x=0, y=0, width=80, rotation=0,
             hinge_x=0, hinge_y=0, confidence=0.7),
    ])
    windows = WindowDetectionResult(windows=[
        Window(type=WindowType.FIXED, x=0, y=0, width=50, height=60,
               rotation=0, orientation=Orientation.HORIZONTAL, confidence=0.55),
    ])
    ocr = OcrResult(texts=[])
    payload = serialize_detection(lines, doors, windows, ocr, processing_ms=1200)

    q = payload["quality"]
    assert q["walls"] == 2
    assert q["doors"] == 1
    assert q["windows"] == 1
    assert q["confidence_avg"] == round((0.7 + 0.55) / 2, 3)
    assert q["processing_ms"] == 1200


def test_quality_confidence_none_when_no_features() -> None:
    lines = LineDetectionResult(lines=[], grouped_lines=[])
    doors = DoorDetectionResult(doors=[])
    windows = WindowDetectionResult(windows=[])
    payload = serialize_detection(lines, doors, windows, OcrResult(texts=[]))
    assert payload["quality"]["confidence_avg"] is None
