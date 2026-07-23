from __future__ import annotations

import re

from app.ocr.schemas import TextCategory

# ── Patrones para clasificación ──────────────────────────────────────────────

SCALE_PATTERNS: list[re.Pattern] = [
    re.compile(r"^\d+\s*[:/]\s*\d+$"),          # 1:100, 1/50
    re.compile(r"^escala\s*\d+\s*[:/]\s*\d+$", re.IGNORECASE),  # ESCALA 1:100
    re.compile(r"^esc\.?\s*\d+", re.IGNORECASE),  # ESC. 1:100
    re.compile(r"^escala$", re.IGNORECASE),       # ESCALA alone
]

MEASUREMENT_PATTERNS: list[re.Pattern] = [
    re.compile(r"^\d+[.,]?\d*\s*(m|cm|mm|mt|ml|km)\s*$", re.IGNORECASE),  # 12.50 m
    re.compile(r"^\d+[.,]?\d*\s*(x|×)\s*\d+[.,]?\d*\s*(m|cm|mm)?$", re.IGNORECASE),  # 3.5×2.8 m
    re.compile(r"^[±]\s*\d+[.,]?\d*\s*(m|cm|mm)?$"),  # ±0.05 m
    re.compile(r"^[+-]\s*\d+[.,]?\d*\s*(m|cm|mm)?$"),  # +0.05 m, -0.05 m
    re.compile(r"^\d+[.,]?\d*$"),                  # just a number (may be measure)
]

ROOM_NAME_PATTERNS: list[re.Pattern] = [
    re.compile(r"^(sala|living|comedor|cocina|baño|dormitorio|habitación|pasillo|hall|"
               r"lavadero|patio|balcón|terraza|garage|cochera|jardín|"
               r"living.?room|bed.?room|bath.?room|kitchen|dining|hall|"
               r"master|suite|estar|office|study|closet|walk.?in|"
               r"lavandería|depósito|archivo|sala.?de.?estar|"
               r"comedor.?diario|toilette|vestidor|distribuidor)"
               r"(\s+\d)?$", re.IGNORECASE),
    re.compile(r"^(dorm\.?|hab\.?|baño\.?|coc\.?|dep\.?)\s*\d*$", re.IGNORECASE),
]

# Words that suggest a note
NOTE_KEYWORDS = [
    "nota:", "notas:", "observación", "observaciones",
    "aclaración", "especificación", "especificaciones",
    "material", "materiales", "acabado", "acabados",
    "detalle", "detalles", "referencia", "referencias",
    "nivel", "niveles", "corte", "cortes", "vista",
]

ROOM_NAME_BLACKLIST = [
    "planta", "corte", "fachada", "vista", "detalle",
    "plano", "proyecto", "plano de", "escala", "nota",
    "superficie", "sup.", "ubicación",
]


class TextClassifier:
    """Classifies OCR text into semantic categories."""

    def classify(self, text: str, confidence: float) -> TextCategory:
        cleaned = text.strip()

        # 1. Scale detection (highest priority — specific pattern)
        for pat in SCALE_PATTERNS:
            if pat.search(cleaned):
                return TextCategory.SCALE

        # 2. Measurement detection
        for i, pat in enumerate(MEASUREMENT_PATTERNS):
            if pat.match(cleaned):
                # Bare numbers below 100 are likely page numbers or labels
                if i == len(MEASUREMENT_PATTERNS) - 1:
                    try:
                        val = float(cleaned.replace(',', '.'))
                        if val < 100:
                            continue
                    except ValueError:
                        pass
                return TextCategory.MEASUREMENT

        # 3. Room name detection
        lower = cleaned.lower()
        for black in ROOM_NAME_BLACKLIST:
            if lower.startswith(black):
                break
        else:
            for pat in ROOM_NAME_PATTERNS:
                if pat.match(cleaned):
                    return TextCategory.ROOM_NAME

        # 4. Note detection
        if any(kw in lower for kw in NOTE_KEYWORDS):
            return TextCategory.NOTE

        if len(cleaned.split()) >= 4:
            return TextCategory.NOTE

        return TextCategory.UNKNOWN

    def is_measurement(self, text: str) -> bool:
        return any(pat.match(text.strip()) for pat in MEASUREMENT_PATTERNS)

    def is_room_name(self, text: str) -> bool:
        cleaned = text.strip()
        lower = cleaned.lower()
        for black in ROOM_NAME_BLACKLIST:
            if lower.startswith(black):
                return False
        return any(pat.match(cleaned) for pat in ROOM_NAME_PATTERNS)
