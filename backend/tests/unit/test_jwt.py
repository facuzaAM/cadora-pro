import pytest
from app.utils.jwt import create_access_token, decode_access_token


def test_create_and_decode_token():
    data = {"sub": "user@example.com", "user_id": "test-id-123"}
    token = create_access_token(data)
    assert isinstance(token, str)
    assert len(token) > 0

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user@example.com"
    assert payload["user_id"] == "test-id-123"


def test_decode_invalid_token():
    result = decode_access_token("invalid.token.here")
    assert result is None


def test_decode_empty_token():
    result = decode_access_token("")
    assert result is None
