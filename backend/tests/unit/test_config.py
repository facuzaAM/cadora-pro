from app.config import Settings


def test_settings_loads():
    settings = Settings()
    assert settings.APP_NAME == "Cadora API"
    assert settings.MAX_FILE_SIZE_MB == 50
    assert settings.JWT_ALGORITHM == "HS256"
    assert ".pdf" in settings.ALLOWED_EXTENSIONS


def test_custom_settings(monkeypatch):
    monkeypatch.setenv("APP_NAME", "Custom API")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("MAX_FILE_SIZE_MB", "100")

    settings = Settings()
    assert settings.APP_NAME == "Custom API"
    assert settings.DEBUG is True
    assert settings.MAX_FILE_SIZE_MB == 100
