"""Tests for the CAD export detection-source resolution and persistence flag.

`_resolve_pipeline` decides where the DXF generator reads detection data from
(edited elements / cached detection / fresh full pipeline). The `persist` flag
tells `generate_cad` whether a freshly-computed full pipeline result should be
stored as the project's ``detection_result``, unifying the worker and the CAD
export on a single source of truth.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.controllers import cad_controller as cc  # noqa: E402
from app.detection.schemas import (  # noqa: E402
    DoorDetectionResult,
    LineDetectionResult,
    WindowDetectionResult,
)
from app.ocr.schemas import OcrResult  # noqa: E402


class _FakeProject:
    def __init__(self, detection_result):
        self.detection_result = detection_result


def _fake_full_result():
    return (
        LineDetectionResult(lines=[], grouped_lines=[]),
        DoorDetectionResult(doors=[]),
        WindowDetectionResult(windows=[]),
        OcrResult(texts=[]),
    )


@pytest.mark.asyncio
async def test_full_pipeline_runs_and_marks_persist(monkeypatch) -> None:
    """No cached result and no edited elements → fresh pipeline, persist=True."""
    async def fake_full(tmp_paths, ds, osvc):
        return _fake_full_result()
    monkeypatch.setattr(cc, "run_full_pipeline", fake_full)

    project = _FakeProject(detection_result=None)
    lines, doors, windows, ocr, persist = await cc._resolve_pipeline(
        project, None, ["a.png"],
    )
    assert persist is True
    assert isinstance(lines, LineDetectionResult)
    assert isinstance(doors, DoorDetectionResult)
    assert isinstance(windows, WindowDetectionResult)
    assert isinstance(ocr, OcrResult)


@pytest.mark.asyncio
async def test_cached_result_reused_without_persist(monkeypatch) -> None:
    """A cached detection_result is reused and must NOT be re-persisted."""
    cached = {
        "lines": {"lines": [], "grouped_lines": []},
        "doors": {"doors": []},
        "windows": {"windows": []},
        "ocr_texts": [],
        "ocr_measurements": [],
        "image_width": 100,
        "image_height": 80,
    }
    async def fake_ocr(tmp, osvc):
        return OcrResult(texts=[])
    monkeypatch.setattr(cc, "run_ocr_only", fake_ocr)

    project = _FakeProject(detection_result=cached)
    lines, doors, windows, ocr, persist = await cc._resolve_pipeline(
        project, None, ["a.png"],
    )
    assert persist is False
    assert isinstance(lines, LineDetectionResult)
    assert len(lines.grouped_lines) == 0


@pytest.mark.asyncio
async def test_edited_elements_never_persists(monkeypatch) -> None:
    """Using edited elements rebuilds the result; never overwrite caching."""
    async def fake_ocr(tmp, osvc):
        return OcrResult(texts=[])
    monkeypatch.setattr(cc, "run_ocr_only", fake_ocr)

    elements = cc.ElementsPayload(walls=[], doors=[], windows=[])
    project = _FakeProject(
        detection_result={"lines": {}, "doors": {}, "windows": {},
                          "image_width": 100, "image_height": 80},
    )
    _, _, _, _, persist = await cc._resolve_pipeline(
        project, elements, ["a.png"],
    )
    assert persist is False
