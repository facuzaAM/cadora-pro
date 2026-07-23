from __future__ import annotations

from uuid import uuid4

from app.ocr.scale import _parse_scale_text, detect_scale_factor
from app.ocr.schemas import OcrResult, OcrTextElement, TextCategory


def _make_ocr_result(scale_texts: list[str]) -> OcrResult:
    elements = [
        OcrTextElement(
            id=uuid4(), text=t, category=TextCategory.SCALE,
            confidence=0.9, bbox=(0, 0, 100, 20),
        )
        for t in scale_texts
    ]
    return OcrResult(texts=elements, scales=elements)


class TestParseScaleText:
    def test_colon_100(self):
        ppm = _parse_scale_text("1:100", 4000)
        assert ppm is not None
        assert ppm > 0
        expected = (300 / 2.54) * 100 * 100
        assert abs(ppm - expected) < 1.0

    def test_slash_50(self):
        ppm = _parse_scale_text("1/50", 4000)
        assert ppm is not None
        assert ppm > 0
        expected = (300 / 2.54) * 100 * 50
        assert abs(ppm - expected) < 1.0

    def test_esc_prefix(self):
        ppm = _parse_scale_text("ESC. 1:200", 4000)
        assert ppm is not None
        assert ppm > 0
        expected = (300 / 2.54) * 100 * 200
        assert abs(ppm - expected) < 1.0

    def test_escala_prefix(self):
        ppm = _parse_scale_text("ESCALA 1:100", 4000)
        assert ppm is not None
        assert ppm > 0

    def test_invalid_text(self):
        assert _parse_scale_text("hello world", 4000) is None

    def test_zero_denominator(self):
        assert _parse_scale_text("1:0", 4000) is None

    def test_zero_numerator(self):
        assert _parse_scale_text("0:100", 4000) is None

    def test_no_number(self):
        assert _parse_scale_text("ESC.", 4000) is None

    def test_whitespace_handling(self):
        ppm = _parse_scale_text("  1 : 50  ", 4000)
        assert ppm is not None

    def test_colon_1_1(self):
        ppm = _parse_scale_text("1:1", 4000)
        assert ppm is not None
        assert ppm > 0


class TestDetectScaleFactor:
    def test_with_scale_text(self):
        ocr = _make_ocr_result(["1:100"])
        ppm = detect_scale_factor(ocr, 4000)
        assert ppm is not None
        assert ppm > 0

    def test_returns_none_when_no_scale(self):
        ocr = OcrResult(texts=[])
        assert detect_scale_factor(ocr, 4000) is None

    def test_prefers_first_valid_scale(self):
        ocr = _make_ocr_result(["1:100", "1:50"])
        ppm = detect_scale_factor(ocr, 4000)
        assert ppm is not None

    def test_ignores_invalid_scales(self):
        elem = OcrTextElement(
            id=uuid4(), text="invalid", category=TextCategory.SCALE,
            confidence=0.5, bbox=(0, 0, 100, 20),
        )
        ocr = OcrResult(texts=[elem], scales=[elem])
        assert detect_scale_factor(ocr, 4000) is None

    def test_multiple_scales_returns_first_valid(self):
        elem1 = OcrTextElement(
            id=uuid4(), text="garbage", category=TextCategory.SCALE,
            confidence=0.5, bbox=(0, 0, 100, 20),
        )
        elem2 = OcrTextElement(
            id=uuid4(), text="1:50", category=TextCategory.SCALE,
            confidence=0.9, bbox=(0, 0, 100, 20),
        )
        ocr = OcrResult(texts=[elem1, elem2], scales=[elem1, elem2])
        ppm = detect_scale_factor(ocr, 4000)
        assert ppm is not None
