"""Scale detection from OCR text.

Parses architectural scale notations (e.g. "1:100", "ESC. 1:50") and
computes a pixels-to-meters conversion factor.
"""

from __future__ import annotations

import re

from app.ocr.schemas import OcrResult, TextCategory


def detect_scale_factor(ocr_result: OcrResult, image_width_px: int) -> float | None:
    """Detect the scale from OCR results and return pixels-per-meter.

    Returns None if no scale is found.

    The conversion factor represents how many pixels correspond to one meter
    in the real world. For example, at 1:100 on a 300 DPI scan, 1 meter
    in reality = 1181.1 pixels (100cm * 300dpi / 2.54).
    """
    for scale_text in ocr_result.scales:
        ppm = _parse_scale_text(scale_text.text, image_width_px)
        if ppm is not None:
            return ppm
    return None


def _parse_scale_text(text: str, image_width_px: int) -> float | None:
    """Parse a scale text like '1:100' and return pixels per meter."""
    cleaned = text.strip().lower()
    cleaned = re.sub(r"^esc(?:ala)?\.?\s*", "", cleaned)

    match = re.match(r"(\d+)\s*[:/]\s*(\d+)", cleaned)
    if not match:
        return None

    num = int(match.group(1))
    den = int(match.group(2))

    if num == 0 or den == 0:
        return None

    scale_ratio = den / num

    standard_dpi = 300
    pixels_per_inch = standard_dpi
    cm_per_inch = 2.54
    pixels_per_cm = pixels_per_inch / cm_per_inch
    pixels_per_meter = pixels_per_cm * 100

    return pixels_per_meter * scale_ratio
