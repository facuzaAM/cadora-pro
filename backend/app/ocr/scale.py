"""Scale detection from OCR text.

Parses architectural scale notations (e.g. "1:100", "ESC. 1:50") and
computes a pixels-to-meters conversion factor.
"""

from __future__ import annotations

import re

from app.ocr.schemas import OcrResult

# DPI at which documents are rasterized for detection (see pdf2image in
# DetectionService). Pixels-per-meter depends on this: using the wrong DPI
# scales the exported CAD wrongly (e.g. 1.5x error if 300 assumed for a 200-DPI
# rasterization). Floor-plan scans are typically >= 150 DPI; 200 matches the
# PDF rasterization, the most common source.
DEFAULT_DPI = 200


def detect_scale_factor(
    ocr_result: OcrResult, image_width_px: int, dpi: int = DEFAULT_DPI,
) -> float | None:
    """Detect the scale from OCR results and return pixels-per-meter.

    Returns None if no scale is found.

    The conversion factor represents how many pixels correspond to one meter
    in the real world. For example, at 1:100 on a 200 DPI rasterization, 1 meter
    in reality = 78.74 pixels on paper (1 cm on paper at 1:100 = 1 real meter,
    and 1 cm at 200 DPI = 200/2.54 = 78.74 px).
    """
    for scale_text in ocr_result.scales:
        ppm = _parse_scale_text(scale_text.text, image_width_px, dpi)
        if ppm is not None:
            return ppm
    return None


def _parse_scale_text(
    text: str, image_width_px: int, dpi: int = DEFAULT_DPI,
) -> float | None:
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

    scale_ratio = num / den

    pixels_per_inch = dpi
    cm_per_inch = 2.54
    pixels_per_cm = pixels_per_inch / cm_per_inch
    pixels_per_meter = pixels_per_cm * 100

    return pixels_per_meter * scale_ratio
