from app.utils.jwt import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)


def test_create_and_decode_access_token():
    data = {"sub": "user@example.com", "user_id": "test-id-123", "token_version": 0}
    token = create_access_token(data)
    assert isinstance(token, str)
    assert len(token) > 0

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user@example.com"
    assert payload["user_id"] == "test-id-123"
    assert payload["token_version"] == 0
    assert payload["type"] == "access"


def test_create_and_decode_refresh_token():
    data = {"sub": "user@example.com", "token_version": 0}
    token = create_refresh_token(data)
    assert isinstance(token, str)
    assert len(token) > 0

    payload = decode_refresh_token(token)
    assert payload is not None
    assert payload["sub"] == "user@example.com"
    assert payload["token_version"] == 0
    assert payload["type"] == "refresh"


def test_decode_access_token_rejects_refresh_token():
    token = create_refresh_token({"sub": "user@example.com"})
    result = decode_access_token(token)
    assert result is None


def test_decode_refresh_token_rejects_access_token():
    token = create_access_token({"sub": "user@example.com"})
    result = decode_refresh_token(token)
    assert result is None


def test_decode_invalid_token():
    result = decode_access_token("invalid.token.here")
    assert result is None


def test_decode_invalid_refresh_token():
    result = decode_refresh_token("invalid.token.here")
    assert result is None


def test_decode_empty_token():
    result = decode_access_token("")
    assert result is None


def test_decode_empty_refresh_token():
    result = decode_refresh_token("")
    assert result is None


def test_tokens_are_different():
    data = {"sub": "user@example.com"}
    access = create_access_token(data)
    refresh = create_refresh_token(data)
    assert access != refresh
