from app.ocr.schemas import OcrResult, OcrTextElement, TextCategory


def test_text_category_values():
    assert TextCategory.MEASUREMENT.value == "measurement"
    assert TextCategory.ROOM_NAME.value == "room_name"
    assert TextCategory.SCALE.value == "scale"
    assert TextCategory.NOTE.value == "note"
    assert TextCategory.UNKNOWN.value == "unknown"


def test_ocr_text_element():
    el = OcrTextElement(
        text="Living Room",
        category=TextCategory.ROOM_NAME,
        confidence=0.95,
        bbox=(10.0, 20.0, 100.0, 50.0),
        font_size=12.0,
        rotation=0.0,
    )
    assert el.text == "Living Room"
    assert el.category == TextCategory.ROOM_NAME
    assert el.confidence == 0.95
    assert el.id is not None


def test_ocr_result():
    el = OcrTextElement(
        text="3.50m",
        category=TextCategory.MEASUREMENT,
        confidence=0.9,
        bbox=(0, 0, 100, 20),
        font_size=10.0,
        rotation=0.0,
    )
    result = OcrResult(
        texts=[el],
        measurements=[el],
        room_names=[],
        scales=[],
        notes=[],
        raw_text="3.50m",
        page_count=1,
    )
    assert len(result.texts) == 1
    assert len(result.measurements) == 1
    assert result.page_count == 1
