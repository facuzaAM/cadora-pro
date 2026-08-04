import pytest
from sqlalchemy import func, select

from app.config import settings
from app.models.paddle_event import PaddleWebhookEvent
from app.services.paddle_service import PaddleService


async def register_user(client, email: str = "billing@example.com"):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Testpass123!", "name": "Billing User"},
    )
    assert resp.status_code == 200
    return resp.json()


def build_subscription_created_payload(
    user_id: str,
    price_id: str,
    event_id: str = "evt_sub_created_1",
):
    return {
        "event_id": event_id,
        "event_type": "subscription.created",
        "occurred_at": "2026-01-15T10:00:00Z",
        "data": {
            "id": "sub_01HQJ3K2Y3",
            "customer_id": "cus_01HQJ3K2Y3",
            "status": "active",
            "custom_data": {"user_id": user_id},
            "customer": {"email": "billing@example.com"},
            "items": [
                {
                    "price": {"id": price_id},
                    "quantity": 1,
                }
            ],
            "next_billing_period": {"ends_at": "2026-02-15T10:00:00Z"},
        },
    }


@pytest.mark.asyncio
async def test_webhook_requires_signature(client):
    resp = await client.post("/api/v1/billing/webhook", json={})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_webhook_invalid_signature(client):
    resp = await client.post(
        "/api/v1/billing/webhook",
        content=b'{"event_id":"x"}',
        headers={"paddle-signature": "ts=1,h1=bad"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_subscription_created_upgrades_plan_and_dedups(client, db_session, monkeypatch):
    monkeypatch.setattr(
        PaddleService, "verify_signature", staticmethod(lambda payload, sig: True)
    )
    monkeypatch.setattr(settings, "PADDLE_PRICE_STARTER", "price_test_starter")

    data = await register_user(client)
    user_id = data["user"]["id"]
    token = data["access_token"]

    payload = build_subscription_created_payload(user_id, settings.PADDLE_PRICE_STARTER)
    payload_bytes = __import__("json").dumps(payload).encode()

    resp = await client.post(
        "/api/v1/billing/webhook",
        content=payload_bytes,
        headers={"paddle-signature": "ts=1,h1=signed"},
    )
    assert resp.status_code == 200

    sub = await client.get(
        "/api/v1/billing/subscription",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sub.status_code == 200
    body = sub.json()
    assert body["plan"] == "starter"
    assert body["status"] == "active"

    # Delivering the same event again must be a no-op (DB-backed dedup).
    resp2 = await client.post(
        "/api/v1/billing/webhook",
        content=payload_bytes,
        headers={"paddle-signature": "ts=1,h1=signed"},
    )
    assert resp2.status_code == 200

    count = (
        await db_session.execute(select(func.count()).select_from(PaddleWebhookEvent))
    ).scalar_one()
    assert count == 1
