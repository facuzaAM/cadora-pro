from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import cv2
import numpy as np
from pdf2image import convert_from_path

from app.detection.door_detector import DoorDetector
from app.detection.line_detector import LineDetector
from app.detection.refine import refine_walls
from app.detection.schemas import DoorDetectionResult, LineDetectionResult, WindowDetectionResult
from app.detection.window_detector import WindowDetector
from app.ocr.preprocessor import ImagePreprocessor

logger = logging.getLogger(__name__)


class DetectionService:
    """Orchestrates detection: load -> preprocess -> detect -> classify -> group -> intersect.

    Heavy OpenCV/Tesseract work is offloaded to a thread pool to avoid
    blocking the FastAPI event loop.
    """

    # Max image dimension used for detection and preview. Uploads are
    # downscaled to this cap so processing time and memory stay bounded.
    DETECT_MAX_DIM = 2000

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

    async def process_file_all(
        self, file_path: str | Path,
    ) -> tuple[LineDetectionResult, DoorDetectionResult, WindowDetectionResult]:
        """Detect lines, doors and windows in one pass.

        Loads and preprocesses the image a single time, then runs the line,
        door and window detectors against the shared intermediate result.
        """
        image = await asyncio.to_thread(self._load_image_from_file, file_path)
        return await asyncio.to_thread(self._process_image_all, image)

    def _process_image_all(
        self, image: np.ndarray,
    ) -> tuple[LineDetectionResult, DoorDetectionResult, WindowDetectionResult]:
        walls_binary, fine_binary = self.preprocessor.detect_pipeline_pair(image)
        lines, grouped, intersections, w, h = self.detector.detect(image, binary=walls_binary)

        # Door/window gap scanning needs the gap-preserving fine binary; the
        # walls binary has its narrow gaps closed away (see preprocessor).
        doors = self.door_detector.detect(image, grouped, lines, binary=fine_binary)
        door_gaps = [
            (d.wall_gap_x1, d.wall_gap_y1, d.wall_gap_x2, d.wall_gap_y2)
            for d in doors.doors
        ]
        windows = self.window_detector.detect(
            image, grouped, binary=fine_binary, excluded_gaps=door_gaps,
        )

        # Drop strokes the doors/windows already explain (leaves, arc chords,
        # glass lines) and split walls that were chained through an opening.
        grouped = refine_walls(grouped, doors.doors, windows.windows)
        intersections = self.detector._find_intersections(grouped, image.shape)

        line_result = LineDetectionResult(
            lines=lines,
            grouped_lines=grouped,
            intersections=intersections,
            image_width=w,
            image_height=h,
        )
        line_result.horizontal = [line for line in grouped if line.category.value == "horizontal"]
        line_result.vertical = [line for line in grouped if line.category.value == "vertical"]
        line_result.diagonal = [line for line in grouped if line.category.value == "diagonal"]

        return line_result, doors, windows

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

    def _process_image_doors(self, image: np.ndarray) -> DoorDetectionResult:
        binary = self.preprocessor.detect_pipeline(image)
        lines, grouped, _, _, _ = self.detector.detect(image, binary=binary)
        return self.door_detector.detect(image, grouped, lines, binary=binary)

    async def process_file_windows(
        self, file_path: str | Path,
    ) -> WindowDetectionResult:
        image = await asyncio.to_thread(self._load_image_from_file, file_path)
        return await asyncio.to_thread(self._process_image_windows, image)

    def _process_image_windows(self, image: np.ndarray) -> WindowDetectionResult:
        binary = self.preprocessor.detect_pipeline(image)
        _, grouped, _, _, _ = self.detector.detect(image, binary=binary)
        return self.window_detector.detect(image, grouped, binary=binary)

    @staticmethod
    def _load_image_from_file(file_path: str | Path) -> np.ndarray:
        path = Path(file_path)
        if path.suffix.lower() in (".pdf",):
            images = DetectionService._pdf_to_images(path)
            return DetectionService._limit_max_dim(images[0])
        return DetectionService._limit_max_dim(DetectionService._load_image(path))

    @staticmethod
    def _load_image(path: Path) -> np.ndarray:
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f"No se pudo cargar la imagen: {path}")
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    @staticmethod
    def _limit_max_dim(image: np.ndarray, max_dim: int = None) -> np.ndarray:
        if max_dim is None:
            max_dim = DetectionService.DETECT_MAX_DIM
        h, w = image.shape[:2]
        max_side = max(h, w)
        if max_side <= max_dim:
            return image
        scale = max_dim / max_side
        size = (int(w * scale), int(h * scale))
        return cv2.resize(image, size, interpolation=cv2.INTER_AREA)

    @staticmethod
    def _pdf_to_images(path: Path, dpi: int = 200) -> list[np.ndarray]:
        pil_images = convert_from_path(str(path), dpi=dpi)
        return [np.array(img) for img in pil_images]
