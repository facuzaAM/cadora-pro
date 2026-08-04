import uuid

import pytest
from starlette.status import HTTP_402_PAYMENT_REQUIRED

from app.services.plan_enforcer import check_storage_limit


async def register_user(client, email: str = "plan@example.com"):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Testpass123!", "name": "Plan User"},
    )
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.asyncio
async def test_conversion_limit_returns_402(client, db_session):
    from sqlalchemy import select

    from app.models.user import User

    data = await register_user(client)
    token = data["access_token"]

    user = (
        await db_session.execute(select(User).where(User.email == "plan@example.com"))
    ).scalar_one()
    user.conversions_used = user.conversions_limit
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/detection/ocr/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {token}"},
        data={"language": "spa+eng"},
        files={"file": ("plano.pdf", b"%PDF-1.4 fake", "application/pdf")},
    )
    assert resp.status_code == 402
    assert "límite" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_storage_limit_check_blocks_oversized_file():
    from app.models.user import User

    user = User(
        email="storage@example.com",
        name="Storage",
        hashed_password="x",
        storage_limit=1024,
        storage_used=1024,
    )
    with pytest.raises(Exception) as excinfo:
        await check_storage_limit(user, file_size=10)
    assert excinfo.value.status_code == HTTP_402_PAYMENT_REQUIRED


@pytest.mark.asyncio
async def test_storage_limit_check_allows_under_limit():
    from app.models.user import User

    user = User(
        email="storage2@example.com",
        name="Storage",
        hashed_password="x",
        storage_limit=1024,
        storage_used=100,
    )
    await check_storage_limit(user, file_size=10)
