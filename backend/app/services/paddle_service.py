from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from uuid import UUID

from paddle_billing.Notifications.Secret import Secret
from paddle_billing.Notifications.Verifier import Verifier
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories.user_repository import UserRepository
from app.services.plan_config import get_plan

logger = logging.getLogger(__name__)

_PROCESSED_EVENTS: dict[str, float] = {}
_EVENT_TTL_SECONDS = 3600


class _WebhookRequest:
    def __init__(self, body: bytes):
        self._body = body

    @property
    def body(self) -> bytes | None:
        return self._body

    @property
    def content(self) -> bytes | None:
        return self._body

    @property
    def data(self) -> bytes | None:
        return self._body


class PaddleService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    @staticmethod
    def verify_signature(payload: bytes, paddle_signature: str) -> bool:
        if not settings.PADDLE_WEBHOOK_SECRET or not paddle_signature:
            return False

        raw_secret: bytes | str = settings.PADDLE_WEBHOOK_SECRET
        if isinstance(raw_secret, str):
            raw_secret = raw_secret.encode("utf-8")

        try:
            secret = Secret(raw_secret)
            verifier = Verifier()
            request = _WebhookRequest(payload)
            verifier.verify(request, secrets=[secret], verify_time_drift=True)
            return True
        except Exception:
            logger.exception("Paddle webhook signature verification failed")
            return False

    @staticmethod
    async def handle_webhook(payload: bytes, paddle_signature: str) -> None:
        if not PaddleService.verify_signature(payload, paddle_signature):
            raise ValueError("Invalid Paddle webhook signature")

        event = json.loads(payload)
        event_type = event.get("event_type", "")
        data = event.get("data", {})
        event_id = event.get("event_id", "")

        if event_id and _is_duplicate_event(event_id):
            logger.info("Duplicate Paddle event ignored: %s (id=%s)", event_type, event_id)
            return

        logger.info("Paddle webhook received: %s", event_type)

        if event_type == "subscription.created":
            await PaddleService._handle_subscription_created(data)
        elif event_type == "subscription.updated":
            await PaddleService._handle_subscription_updated(data)
        elif event_type == "subscription.cancelled":
            await PaddleService._handle_subscription_cancelled(data)
        elif event_type == "subscription.paused":
            await PaddleService._handle_subscription_paused(data)
        elif event_type == "transaction.completed":
            await PaddleService._handle_transaction_completed(data)
        else:
            logger.debug("Unhandled Paddle event: %s", event_type)

    @staticmethod
    async def _handle_subscription_created(data: dict) -> None:
        custom_data = data.get("custom_data", {})
        user_id = custom_data.get("user_id") if custom_data else None
        plan_name = custom_data.get("plan") if custom_data else None

        paddle_customer_id = data.get("customer_id", "")
        paddle_subscription_id = data.get("id", "")
        status = data.get("status", "active")

        if not user_id:
            logger.warning("subscription.created missing user_id in custom_data")
            return

        from app.database import async_session_factory

        async with async_session_factory() as db:
            repo = UserRepository(db)
            user = await repo.get_by_id(UUID(user_id))
            if not user:
                logger.warning("subscription.created: user %s not found", user_id)
                return

            plan = get_plan(plan_name or "free")
            now = datetime.now(UTC)

            user.subscription_plan = plan_name or "free"
            user.subscription_status = _map_paddle_status(status)
            user.conversions_limit = plan.conversions_limit
            user.storage_limit = plan.storage_limit
            user.priority_processing = plan.priority_processing
            user.paddle_customer_id = str(paddle_customer_id) or user.paddle_customer_id
            user.paddle_subscription_id = str(paddle_subscription_id)
            user.conversions_used = 0
            user.conversions_reset_at = now

            renewal_date = data.get("renewal_date")
            if renewal_date:
                user.subscription_end = datetime.fromisoformat(
                    renewal_date.replace("Z", "+00:00")
                )

            await repo._save(user)
            await db.commit()

    @staticmethod
    async def _handle_subscription_updated(data: dict) -> None:
        paddle_subscription_id = data.get("id", "")
        paddle_customer_id = data.get("customer_id", "")
        status = data.get("status", "active")

        from app.database import async_session_factory

        async with async_session_factory() as db:
            repo = UserRepository(db)
            user = await repo.get_by_paddle_subscription(str(paddle_subscription_id))
            if not user and paddle_customer_id:
                user = await repo.get_by_paddle_customer(str(paddle_customer_id))
            if not user:
                return

            items = data.get("items", [])
            if not items:
                logger.warning(
                    "subscription.updated sin items para %s",
                    paddle_subscription_id,
                )
                return
            price_id = items[0].get("price", {}).get("id", "")

            _price_to_plan = {
                settings.PADDLE_PRICE_STARTER: "starter",
                settings.PADDLE_PRICE_PRO: "pro",
                settings.PADDLE_PRICE_BUSINESS: "business",
            }
            plan_name = _price_to_plan.get(price_id, "free")
            if plan_name == "free" and price_id:
                logger.warning(
                    "Paddle price_id %s no matchea ningun plan. "
                    "Degradando a 'free' para subscription %s",
                    price_id, paddle_subscription_id,
                )

            plan = get_plan(plan_name)
            user.subscription_plan = plan_name
            user.subscription_status = _map_paddle_status(status)
            user.conversions_limit = plan.conversions_limit
            user.storage_limit = plan.storage_limit
            user.priority_processing = plan.priority_processing

            renewal_date = data.get("renewal_date")
            if renewal_date:
                user.subscription_end = datetime.fromisoformat(
                    renewal_date.replace("Z", "+00:00")
                )

            await repo._save(user)
            await db.commit()

    @staticmethod
    async def _handle_subscription_cancelled(data: dict) -> None:
        paddle_subscription_id = data.get("id", "")
        paddle_customer_id = data.get("customer_id", "")

        from app.database import async_session_factory

        async with async_session_factory() as db:
            repo = UserRepository(db)
            user = await repo.get_by_paddle_subscription(str(paddle_subscription_id))
            if not user and paddle_customer_id:
                user = await repo.get_by_paddle_customer(str(paddle_customer_id))
            if not user:
                return

            now = datetime.now(UTC)
            free_plan = get_plan("free")
            user.subscription_plan = "free"
            user.subscription_status = "canceled"
            user.conversions_limit = free_plan.conversions_limit
            user.storage_limit = free_plan.storage_limit
            user.priority_processing = free_plan.priority_processing
            user.conversions_used = 0
            user.conversions_reset_at = now
            user.subscription_end = None
            await repo._save(user)
            await db.commit()

    @staticmethod
    async def _handle_subscription_paused(data: dict) -> None:
        paddle_subscription_id = data.get("id", "")

        from app.database import async_session_factory

        async with async_session_factory() as db:
            repo = UserRepository(db)
            user = await repo.get_by_paddle_subscription(str(paddle_subscription_id))
            if not user:
                return

            user.subscription_status = "paused"
            await repo._save(user)
            await db.commit()

    @staticmethod
    async def _handle_transaction_completed(data: dict) -> None:
        subscription_id = data.get("subscription_id")
        if not subscription_id:
            return

        from app.database import async_session_factory

        async with async_session_factory() as db:
            repo = UserRepository(db)
            user = await repo.get_by_paddle_subscription(str(subscription_id))
            if not user:
                return

            now = datetime.now(UTC)
            user.subscription_status = "active"
            user.conversions_used = 0
            user.conversions_reset_at = now

            items = data.get("items", [])
            if items:
                price_id = items[0].get("price", {}).get("id", "")
                _price_to_plan = {
                    settings.PADDLE_PRICE_STARTER: "starter",
                    settings.PADDLE_PRICE_PRO: "pro",
                    settings.PADDLE_PRICE_BUSINESS: "business",
                }
                plan_name = _price_to_plan.get(price_id, "free")
                if plan_name != "free":
                    plan = get_plan(plan_name)
                    user.subscription_plan = plan_name
                    user.conversions_limit = plan.conversions_limit
                    user.storage_limit = plan.storage_limit
                    user.priority_processing = plan.priority_processing

                period_end = items[0].get("next_transaction", {}).get("created_at")
                if period_end:
                    user.subscription_end = datetime.fromisoformat(
                        period_end.replace("Z", "+00:00")
                    )

            await repo._save(user)
            await db.commit()


def _is_duplicate_event(event_id: str) -> bool:
    now = time.time()
    expired = [k for k, v in _PROCESSED_EVENTS.items() if now - v > _EVENT_TTL_SECONDS]
    for k in expired:
        del _PROCESSED_EVENTS[k]

    if event_id in _PROCESSED_EVENTS:
        return True
    _PROCESSED_EVENTS[event_id] = now
    return False


def _map_paddle_status(paddle_status: str) -> str:
    mapping = {
        "active": "active",
        "canceled": "canceled",
        "past_due": "past_due",
        "paused": "paused",
        "trialing": "active",
        "non_renewing": "active",
    }
    return mapping.get(paddle_status, "inactive")
