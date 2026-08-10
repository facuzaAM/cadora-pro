import asyncio

import cv2
import numpy as np
import pytest

from app.detection.service import DetectionService


def _write_floor_plan(tmp_path, size=(1200, 1600)) -> str:
    img = np.full((size[0], size[1], 3), 255, dtype=np.uint8)
    h, w = size
    cv2.rectangle(img, (50, 50), (w - 50, h - 50), (0, 0, 0), 3)
    cv2.line(img, (50, h // 2), (w - 50, h // 2), (0, 0, 0), 3)
    cv2.putText(img, "SALA 5x6", (w // 2, h // 2 + 50), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    path = str(tmp_path / "plano.png")
    cv2.imwrite(path, img)
    return path


@pytest.mark.asyncio
async def test_process_file_loads_and_detects(tmp_path):
    path = _write_floor_plan(tmp_path)
    service = DetectionService()
    result = await service.process_file(path)
    assert result.image_width == 1600
    assert result.image_height == 1200


@pytest.mark.asyncio
async def test_process_file_all_returns_lines_doors_windows(tmp_path):
    path = _write_floor_plan(tmp_path)
    service = DetectionService()
    lines, doors, windows = await service.process_file_all(path)
    assert lines.image_width == 1600
    assert doors.image_width == 1600
    assert windows.image_width == 1600


@pytest.mark.asyncio
async def test_load_image_caps_max_dimension(tmp_path):
    img = np.full((3000, 5000, 3), 255, dtype=np.uint8)
    path = str(tmp_path / "big.png")
    cv2.imwrite(path, img)
    image = await asyncio.to_thread(DetectionService._load_image_from_file, path)
    assert max(image.shape[:2]) <= DetectionService.DETECT_MAX_DIM
