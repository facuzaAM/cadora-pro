from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import cv2
import numpy as np
from pdf2image import convert_from_path

from app.detection.door_detector import DoorDetector
from app.detection.line_detector import LineDetector
from app.detection.schemas import DoorDetectionResult, LineDetectionResult, WindowDetectionResult
from app.detection.window_detector import WindowDetector
from app.ocr.preprocessor import ImagePreprocessor

logger = logging.getLogger(__name__)


class DetectionService:
    """Orchestrates detection: load -> preprocess -> detect -> classify -> group -> intersect.

    Heavy OpenCV/Tesseract work is offloaded to a thread pool to avoid
    blocking the FastAPI event loop.
    """

    def __init__(self):
        self.preprocessor = ImagePreprocessor()
        self.detector = LineDetector()
        self.door_detector = DoorDetector()
        self.window_detector = WindowDetector()

    async def process_file(
        self, file_path: str | Path,
    ) -> LineDetectionResult:
        image = await asyncio.to_thread(self._load_image_from_file, file_path)
        return await asyncio.to_thread(self._process_image, image)

    async def process_image(self, image: np.ndarray) -> LineDetectionResult:
        return await asyncio.to_thread(self._process_image, image)

    def _process_image(self, image: np.ndarray) -> LineDetectionResult:
        binary = self.preprocessor.detect_pipeline(image)
        lines, grouped, intersections, w, h = self.detector.detect(image, binary=binary)

        result = LineDetectionResult(
            lines=lines,
            grouped_lines=grouped,
            intersections=intersections,
            image_width=w,
            image_height=h,
        )
        result.horizontal = [line for line in lines if line.category.value == "horizontal"]
        result.vertical = [line for line in lines if line.category.value == "vertical"]
        result.diagonal = [line for line in lines if line.category.value == "diagonal"]
        return result

    async def process_file_doors(
        self, file_path: str | Path,
    ) -> DoorDetectionResult:
        image = await asyncio.to_thread(self._load_image_from_file, file_path)
        return await asyncio.to_thread(self._process_image_doors, image)

    async def process_image_doors(self, image: np.ndarray) -> DoorDetectionResult:
        return await asyncio.to_thread(self._process_image_doors, image)

    def _process_image_doors(self, image: np.ndarray) -> DoorDetectionResult:
        binary = self.preprocessor.detect_pipeline(image)
        lines, grouped, _, _, _ = self.detector.detect(image, binary=binary)
        return self.door_detector.detect(image, grouped, lines, binary=binary)

    async def process_file_windows(
        self, file_path: str | Path,
    ) -> WindowDetectionResult:
        image = await asyncio.to_thread(self._load_image_from_file, file_path)
        return await asyncio.to_thread(self._process_image_windows, image)

    async def process_image_windows(self, image: np.ndarray) -> WindowDetectionResult:
        return await asyncio.to_thread(self._process_image_windows, image)

    def _process_image_windows(self, image: np.ndarray) -> WindowDetectionResult:
        binary = self.preprocessor.detect_pipeline(image)
        _, grouped, _, _, _ = self.detector.detect(image, binary=binary)
        return self.window_detector.detect(image, grouped, binary=binary)

    async def process_all(
        self, file_path: str | Path,
    ) -> dict:
        """Run all detectors in one pass (lines + doors + windows)."""
        image = await asyncio.to_thread(self._load_image_from_file, file_path)
        return await asyncio.to_thread(self._process_all_image, image)

    async def process_all_image(self, image: np.ndarray) -> dict:
        return await asyncio.to_thread(self._process_all_image, image)

    def _process_all_image(self, image: np.ndarray) -> dict:
        binary = self.preprocessor.detect_pipeline(image)
        lines, grouped, intersections, w, h = self.detector.detect(image, binary=binary)

        line_result = LineDetectionResult(
            lines=lines,
            grouped_lines=grouped,
            intersections=intersections,
            image_width=w,
            image_height=h,
        )
        line_result.horizontal = [line for line in lines if line.category.value == "horizontal"]
        line_result.vertical = [line for line in lines if line.category.value == "vertical"]
        line_result.diagonal = [line for line in lines if line.category.value == "diagonal"]

        door_result = self.door_detector.detect(image, grouped, lines, binary=binary)
        window_result = self.window_detector.detect(image, grouped, binary=binary)

        return {
            "lines": line_result,
            "doors": door_result,
            "windows": window_result,
        }

    def to_json(self, result: LineDetectionResult, indent: int = 2) -> str:
        return result.model_dump_json(indent=indent)

    @staticmethod
    def _load_image_from_file(file_path: str | Path) -> np.ndarray:
        path = Path(file_path)
        if path.suffix.lower() in (".pdf",):
            images = DetectionService._pdf_to_images(path)
            return images[0]
        return DetectionService._load_image(path)

    @staticmethod
    def _load_image(path: Path) -> np.ndarray:
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f"No se pudo cargar la imagen: {path}")
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    @staticmethod
    def _pdf_to_images(path: Path, dpi: int = 200) -> list[np.ndarray]:
        pil_images = convert_from_path(str(path), dpi=dpi)
        return [np.array(img) for img in pil_images]
