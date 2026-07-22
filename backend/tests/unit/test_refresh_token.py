import uuid
from datetime import datetime, timedelta, timezone

from app.models.refresh_token import RefreshToken


def test_refresh_token_model_fields():
    rt = RefreshToken(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        token="test-jwt-token-string",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        revoked=False,
        created_at=datetime.now(timezone.utc),
    )
    assert rt.revoked is False
    assert rt.expires_at > datetime.now(timezone.utc)
    assert rt.token == "test-jwt-token-string"


def test_refresh_token_defaults():
    rt = RefreshToken(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        token="some-token",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        revoked=False,
    )
    assert rt.revoked is False
    assert rt.created_at is None
