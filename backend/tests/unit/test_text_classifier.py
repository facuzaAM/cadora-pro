from __future__ import annotations

import pytest

from app.ocr.classifier import TextClassifier
from app.ocr.schemas import TextCategory


@pytest.fixture
def clf() -> TextClassifier:
    return TextClassifier()


class TestScaleDetection:
    def test_1_100(self, clf: TextClassifier):
        assert clf.classify("1:100", 0.9) == TextCategory.SCALE

    def test_1_50(self, clf: TextClassifier):
        assert clf.classify("1/50", 0.9) == TextCategory.SCALE

    def test_escala_1_50(self, clf: TextClassifier):
        assert clf.classify("ESCALA 1/50", 0.9) == TextCategory.SCALE

    def test_esc_1_200(self, clf: TextClassifier):
        assert clf.classify("ESC. 1:200", 0.9) == TextCategory.SCALE

    def test_escala_word_only(self, clf: TextClassifier):
        assert clf.classify("ESCALA", 0.9) == TextCategory.SCALE


class TestMeasurementDetection:
    def test_12_50_m(self, clf: TextClassifier):
        assert clf.classify("12.50 m", 0.9) == TextCategory.MEASUREMENT

    def test_3_5x2_8_m(self, clf: TextClassifier):
        assert clf.classify("3.5x2.8 m", 0.9) == TextCategory.MEASUREMENT

    def test_5_cm(self, clf: TextClassifier):
        assert clf.classify("5 cm", 0.9) == TextCategory.MEASUREMENT

    def test_100_mm(self, clf: TextClassifier):
        assert clf.classify("100 mm", 0.9) == TextCategory.MEASUREMENT

    def test_bare_number_below_100_is_unknown(self, clf: TextClassifier):
        assert clf.classify("42", 0.9) == TextCategory.UNKNOWN

    def test_bare_number_above_100_is_measurement(self, clf: TextClassifier):
        assert clf.classify("150", 0.9) == TextCategory.MEASUREMENT

    def test_comma_decimal(self, clf: TextClassifier):
        assert clf.classify("12,50 m", 0.9) == TextCategory.MEASUREMENT


class TestRoomNameDetection:
    def test_cocina(self, clf: TextClassifier):
        assert clf.classify("COCINA", 0.9) == TextCategory.ROOM_NAME

    def test_dormitorio_1(self, clf: TextClassifier):
        assert clf.classify("DORMITORIO 1", 0.9) == TextCategory.ROOM_NAME

    def test_bano(self, clf: TextClassifier):
        assert clf.classify("BAÑO", 0.9) == TextCategory.ROOM_NAME

    def test_living(self, clf: TextClassifier):
        assert clf.classify("LIVING", 0.9) == TextCategory.ROOM_NAME

    def test_sala_de_estar(self, clf: TextClassifier):
        assert clf.classify("SALA DE ESTAR", 0.9) == TextCategory.ROOM_NAME

    def test_dorm_abbr(self, clf: TextClassifier):
        assert clf.classify("DORM. 1", 0.9) == TextCategory.ROOM_NAME

    def test_blacklist_planta(self, clf: TextClassifier):
        assert clf.classify("PLANTA", 0.9) != TextCategory.ROOM_NAME

    def test_blacklist_escala(self, clf: TextClassifier):
        assert clf.classify("ESCALA", 0.9) != TextCategory.ROOM_NAME

    def test_blacklist_nota(self, clf: TextClassifier):
        assert clf.classify("NOTA", 0.9) != TextCategory.ROOM_NAME


class TestNoteDetection:
    def test_material_concreto(self, clf: TextClassifier):
        assert clf.classify("material: concreto armado", 0.9) == TextCategory.NOTE

    def test_acabados(self, clf: TextClassifier):
        assert clf.classify("ACABADOS", 0.9) == TextCategory.NOTE

    def test_observaciones(self, clf: TextClassifier):
        assert clf.classify("OBSERVACIONES", 0.9) == TextCategory.NOTE

    def test_long_text_is_note(self, clf: TextClassifier):
        text = "esto es una nota larga con mucho texto descriptivo"
        assert clf.classify(text, 0.9) == TextCategory.NOTE

    def test_detalle(self, clf: TextClassifier):
        assert clf.classify("DETALLE A", 0.9) == TextCategory.NOTE


class TestUnknownDetection:
    def test_random_short_text(self, clf: TextClassifier):
        assert clf.classify("abc", 0.9) == TextCategory.UNKNOWN

    def test_single_letter(self, clf: TextClassifier):
        assert clf.classify("A", 0.9) == TextCategory.UNKNOWN


class TestIsMeasurement:
    def test_valid(self, clf: TextClassifier):
        assert clf.is_measurement("12.50 m") is True

    def test_invalid(self, clf: TextClassifier):
        assert clf.is_measurement("COCINA") is False

    def test_bare_small_number(self, clf: TextClassifier):
        assert clf.is_measurement("42") is True


class TestIsRoomName:
    def test_valid_room(self, clf: TextClassifier):
        assert clf.is_room_name("COCINA") is True

    def test_blacklisted_word(self, clf: TextClassifier):
        assert clf.is_room_name("PLANTA BAJA") is False

    def test_not_room(self, clf: TextClassifier):
        assert clf.is_room_name("12.50 m") is False
