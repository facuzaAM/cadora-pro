from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytesseract
from pytesseract import Output

from app.ocr.schemas import OcrTextElement, TextCategory


@dataclass
class OcrRawElement:
    text: str
    confidence: float
    x: int
    y: int
    w: int
    h: int


class OcrEngine:
    """Wrapper around Tesseract OCR with bounding-box extraction."""

    def __init__(self, lang: str = "spa+eng"):
        self.lang = lang

    def extract(self, image: np.ndarray) -> list[OcrRawElement]:
        data = pytesseract.image_to_data(
            image,
            lang=self.lang,
            output_type=Output.DICT,
            config="--psm 3 --oem 3",
        )

        elements: list[OcrRawElement] = []
        for i in range(len(data["text"])):
            text = (data["text"][i] or "").strip()
            conf = float(data["conf"][i])
            if not text or conf < 20:
                continue

            elements.append(
                OcrRawElement(
                    text=text,
                    confidence=conf / 100.0,
                    x=data["left"][i],
                    y=data["top"][i],
                    w=data["width"][i],
                    h=data["height"][i],
                )
            )

        return elements

    def extract_raw_text(self, image: np.ndarray) -> str:
        return pytesseract.image_to_string(image, lang=self.lang, config="--psm 3 --oem 3")

    def to_domain(self, raw: OcrRawElement, category: TextCategory) -> OcrTextElement:
        return OcrTextElement(
            text=raw.text,
            category=category,
            confidence=raw.confidence,
            bbox=(
                float(raw.x),
                float(raw.y),
                float(raw.x + raw.w),
                float(raw.y + raw.h),
            ),
            font_size=float(raw.h),
        )
