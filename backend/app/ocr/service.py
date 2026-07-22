from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import cv2
import numpy as np
from pdf2image import convert_from_path

from app.ocr.schemas import OcrRequest, OcrResult, TextCategory
from app.ocr.engine import OcrEngine
from app.ocr.classifier import TextClassifier
from app.ocr.preprocessor import ImagePreprocessor

logger = logging.getLogger(__name__)


class OcrService:
    """Orchestrates the full OCR pipeline: load -> preprocess -> extract -> classify.

    Heavy Tesseract/OpenCV work is offloaded to a thread pool.
    """

    def __init__(self):
        self.engine = OcrEngine()
        self.classifier = TextClassifier()
        self.preprocessor = ImagePreprocessor()

    async def process_file(
        self,
        file_path: str | Path,
        request: OcrRequest | None = None,
        dpi: int = 72,
    ) -> OcrResult:
        return await asyncio.to_thread(self._process_file_sync, file_path, request, dpi)

    def _process_file_sync(
        self,
        file_path: str | Path,
        request: OcrRequest | None = None,
        dpi: int = 72,
    ) -> OcrResult:
        opts = request or OcrRequest()
        path = Path(file_path)

        if path.suffix.lower() in (".pdf",):
            images = self._pdf_to_images(path, dpi=dpi)
        else:
            images = [self._load_image(path)]

        all_texts = []
        raw_parts = []
        for image in images:
            processed = self.preprocessor.pipeline(image, dpi=dpi)
            raw_elements = self.engine.extract(processed)

            page_texts = []
            for raw in raw_elements:
                category = self._classify_with_options(raw.text, opts)
                element = self.engine.to_domain(raw, category)
                page_texts.append(element)
                raw_parts.append(raw.text)
            all_texts.extend(page_texts)

        raw_text = " ".join(raw_parts)

        return self._build_result(all_texts, raw_text, len(images))

    async def process_image(
        self,
        image: np.ndarray,
        request: OcrRequest | None = None,
        dpi: int = 72,
    ) -> OcrResult:
        return await asyncio.to_thread(self._process_image_sync, image, request, dpi)

    def _process_image_sync(
        self,
        image: np.ndarray,
        request: OcrRequest | None = None,
        dpi: int = 72,
    ) -> OcrResult:
        opts = request or OcrRequest()
        processed = self.preprocessor.pipeline(image, dpi=dpi)
        raw_elements = self.engine.extract(processed)

        texts = []
        raw_parts = []
        for raw in raw_elements:
            category = self._classify_with_options(raw.text, opts)
            texts.append(self.engine.to_domain(raw, category))
            raw_parts.append(raw.text)

        raw_text = " ".join(raw_parts)
        return self._build_result(texts, raw_text, 1)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _classify_with_options(self, text: str, opts: OcrRequest) -> TextCategory:
        category = self.classifier.classify(text, 1.0)

        if category == TextCategory.MEASUREMENT and not opts.detect_measurements:
            return TextCategory.UNKNOWN
        if category == TextCategory.ROOM_NAME and not opts.detect_room_names:
            return TextCategory.UNKNOWN
        if category == TextCategory.SCALE and not opts.detect_scales:
            return TextCategory.UNKNOWN
        if category == TextCategory.NOTE and not opts.detect_notes:
            return TextCategory.UNKNOWN

        return category

    def _build_result(self, texts: list, raw_text: str, page_count: int) -> OcrResult:
        result = OcrResult(texts=texts, raw_text=raw_text, page_count=page_count)
        result.measurements = [t for t in texts if t.category == TextCategory.MEASUREMENT]
        result.room_names = [t for t in texts if t.category == TextCategory.ROOM_NAME]
        result.scales = [t for t in texts if t.category == TextCategory.SCALE]
        result.notes = [t for t in texts if t.category == TextCategory.NOTE]
        return result

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
