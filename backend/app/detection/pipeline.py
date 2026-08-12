from __future__ import annotations

import asyncio
import logging

from app.detection.schemas import (
    DoorDetectionResult,
    LineDetectionResult,
    WindowDetectionResult,
)
from app.detection.service import DetectionService
from app.ocr.schemas import OcrResult
from app.ocr.service import OcrService

logger = logging.getLogger(__name__)


def _merge_line_results(results: list[LineDetectionResult]) -> LineDetectionResult:
    merged = LineDetectionResult(
        lines=[], horizontal=[], vertical=[], diagonal=[],
        grouped_lines=[], intersections=[],
    )
    for r in results:
        merged.lines.extend(r.lines)
        merged.horizontal.extend(r.horizontal)
        merged.vertical.extend(r.vertical)
        merged.diagonal.extend(r.diagonal)
        merged.grouped_lines.extend(r.grouped_lines)
        merged.intersections.extend(r.intersections)
        if r.image_width > merged.image_width:
            merged.image_width = r.image_width
        if r.image_height > merged.image_height:
            merged.image_height = r.image_height
    return merged


def _merge_door_results(results: list[DoorDetectionResult]) -> DoorDetectionResult:
    merged = DoorDetectionResult(doors=[], image_width=0, image_height=0)
    for r in results:
        merged.doors.extend(r.doors)
        if r.image_width > merged.image_width:
            merged.image_width = r.image_width
        if r.image_height > merged.image_height:
            merged.image_height = r.image_height
    return merged


def _merge_window_results(results: list[WindowDetectionResult]) -> WindowDetectionResult:
    merged = WindowDetectionResult(windows=[], image_width=0, image_height=0)
    for r in results:
        merged.windows.extend(r.windows)
        if r.image_width > merged.image_width:
            merged.image_width = r.image_width
        if r.image_height > merged.image_height:
            merged.image_height = r.image_height
    return merged


def _merge_ocr_results(results: list[OcrResult]) -> OcrResult:
    merged = OcrResult(
        texts=[], measurements=[], room_names=[], scales=[], notes=[],
        raw_text="", page_count=0,
    )
    for r in results:
        merged.texts.extend(r.texts)
        merged.measurements.extend(r.measurements)
        merged.room_names.extend(r.room_names)
        merged.scales.extend(r.scales)
        merged.notes.extend(r.notes)
        if merged.raw_text and r.raw_text:
            merged.raw_text += "\n" + r.raw_text
        elif r.raw_text:
            merged.raw_text = r.raw_text
        merged.page_count += r.page_count
    return merged


# Process at most N pages concurrently. Detection + OCR hold full-resolution
# images in memory, so firing off every page of a large multi-page plan at once
# can exhaust RAM (docker mem_limit). A small cap keeps peak memory bounded
# while still overlapping I/O between pages.
MAX_CONCURRENT_PAGES = 2
_pipeline_semaphore = asyncio.Semaphore(MAX_CONCURRENT_PAGES)


async def _process_file(
    path: str,
    detection_service: DetectionService,
    ocr_service: OcrService,
) -> tuple[LineDetectionResult, DoorDetectionResult, WindowDetectionResult, OcrResult]:
    """Run detection (single preprocessing pass) and OCR for one file.

    Both workloads are dispatched concurrently; detection and OCR each push
    their heavy work to the thread pool, so this halves wall-clock time.
    """
    detection = detection_service.process_file_all(path)
    ocr = ocr_service.process_file(path)
    (lines, doors, windows), ocr_result = await asyncio.gather(detection, ocr)
    return lines, doors, windows, ocr_result


async def run_full_pipeline(
    temp_paths: list[str],
    detection_service: DetectionService,
    ocr_service: OcrService,
) -> tuple[LineDetectionResult, DoorDetectionResult, WindowDetectionResult, OcrResult]:
    async def bounded(path: str):
        async with _pipeline_semaphore:
            return await _process_file(path, detection_service, ocr_service)

    results = await asyncio.gather(*(bounded(path) for path in temp_paths))

    line_results = [r[0] for r in results]
    door_results = [r[1] for r in results]
    window_results = [r[2] for r in results]
    ocr_results = [r[3] for r in results]

    return (
        _merge_line_results(line_results),
        _merge_door_results(door_results),
        _merge_window_results(window_results),
        _merge_ocr_results(ocr_results),
    )


async def run_ocr_only(
    temp_paths: list[str],
    ocr_service: OcrService,
) -> OcrResult:
    results = [await ocr_service.process_file(path) for path in temp_paths]
    return _merge_ocr_results(results)


def serialize_detection(
    lines_result: LineDetectionResult,
    doors_result: DoorDetectionResult,
    windows_result: WindowDetectionResult,
    ocr_result: OcrResult,
) -> dict:
    return {
        "lines": lines_result.model_dump(mode="json"),
        "doors": doors_result.model_dump(mode="json"),
        "windows": windows_result.model_dump(mode="json"),
        "ocr_texts": [t.model_dump(mode="json") for t in ocr_result.texts],
        "ocr_measurements": [m.model_dump(mode="json") for m in ocr_result.measurements],
        "image_width": max(
            lines_result.image_width,
            doors_result.image_width,
            windows_result.image_width,
        ),
        "image_height": max(
            lines_result.image_height,
            doors_result.image_height,
            windows_result.image_height,
        ),
    }


def load_detection(
    payload: dict,
) -> tuple[LineDetectionResult, DoorDetectionResult, WindowDetectionResult]:
    lines = LineDetectionResult.model_validate(payload["lines"])
    doors = DoorDetectionResult.model_validate(payload["doors"])
    windows = WindowDetectionResult.model_validate(payload["windows"])
    return lines, doors, windows
