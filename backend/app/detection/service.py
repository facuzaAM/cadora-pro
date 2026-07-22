from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np
from pdf2image import convert_from_path

from app.detection.schemas import LineDetectionResult, DoorDetectionResult, WindowDetectionResult
from app.detection.line_detector import LineDetector
from app.detection.door_detector import DoorDetector
from app.detection.window_detector import WindowDetector
from app.ocr.preprocessor import ImagePreprocessor

logger = logging.getLogger(__name__)


class DetectionService:
    """Orchestrates detection: load → preprocess → detect → classify → group → intersect.

    The image is preprocessed once and the binary result is shared across
    line, door, and window detectors for consistency and performance.
    """

    def __init__(self):
        self.preprocessor = ImagePreprocessor()
        self.detector = LineDetector()
        self.door_detector = DoorDetector()
        self.window_detector = WindowDetector()

    async def process_file(
        self, file_path: str | Path,
    ) -> LineDetectionResult:
        path = Path(file_path)
        if path.suffix.lower() in (".pdf",):
            images = self._pdf_to_images(path)
            image = images[0]
        else:
            image = self._load_image(path)

        return self._process_image(image)

    async def process_image(self, image: np.ndarray) -> LineDetectionResult:
        return self._process_image(image)

    def _process_image(self, image: np.ndarray) -> LineDetectionResult:
        lines, grouped, intersections, w, h = self.detector.detect(image)

        result = LineDetectionResult(
            lines=lines,
            grouped_lines=grouped,
            intersections=intersections,
            image_width=w,
            image_height=h,
        )
        result.horizontal = [l for l in lines if l.category.value == "horizontal"]
        result.vertical = [l for l in lines if l.category.value == "vertical"]
        result.diagonal = [l for l in lines if l.category.value == "diagonal"]
        return result

    async def process_file_doors(
        self, file_path: str | Path,
    ) -> DoorDetectionResult:
        path = Path(file_path)
        if path.suffix.lower() in (".pdf",):
            images = self._pdf_to_images(path)
            image = images[0]
        else:
            image = self._load_image(path)

        return self._process_image_doors(image)

    async def process_image_doors(self, image: np.ndarray) -> DoorDetectionResult:
        return self._process_image_doors(image)

    def _process_image_doors(self, image: np.ndarray) -> DoorDetectionResult:
        lines, grouped, _, _, _ = self.detector.detect(image)
        return self.door_detector.detect(image, grouped, lines)

    async def process_file_windows(
        self, file_path: str | Path,
    ) -> WindowDetectionResult:
        path = Path(file_path)
        if path.suffix.lower() in (".pdf",):
            images = self._pdf_to_images(path)
            image = images[0]
        else:
            image = self._load_image(path)
        return self._process_image_windows(image)

    async def process_image_windows(self, image: np.ndarray) -> WindowDetectionResult:
        return self._process_image_windows(image)

    def _process_image_windows(self, image: np.ndarray) -> WindowDetectionResult:
        _, grouped, _, _, _ = self.detector.detect(image)
        return self.window_detector.detect(image, grouped)

    async def process_all(
        self, file_path: str | Path,
    ) -> dict:
        """Run all detectors in one pass (lines + doors + windows)."""
        path = Path(file_path)
        if path.suffix.lower() in (".pdf",):
            images = self._pdf_to_images(path)
            image = images[0]
        else:
            image = self._load_image(path)
        return self._process_all_image(image)

    async def process_all_image(self, image: np.ndarray) -> dict:
        return self._process_all_image(image)

    def _process_all_image(self, image: np.ndarray) -> dict:
        lines, grouped, intersections, w, h = self.detector.detect(image)

        line_result = LineDetectionResult(
            lines=lines,
            grouped_lines=grouped,
            intersections=intersections,
            image_width=w,
            image_height=h,
        )
        line_result.horizontal = [l for l in lines if l.category.value == "horizontal"]
        line_result.vertical = [l for l in lines if l.category.value == "vertical"]
        line_result.diagonal = [l for l in lines if l.category.value == "diagonal"]

        door_result = self.door_detector.detect(image, grouped, lines)
        window_result = self.window_detector.detect(image, grouped)

        return {
            "lines": line_result,
            "doors": door_result,
            "windows": window_result,
        }

    def to_json(self, result: LineDetectionResult, indent: int = 2) -> str:
        return result.model_dump_json(indent=indent)

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
