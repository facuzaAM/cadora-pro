from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from paddle_billing.Client import Client
from paddle_billing.Environment import Environment
from paddle_billing.Notifications.Secret import Secret
from paddle_billing.Notifications.Verifier import Verifier
from paddle_billing.Options import Options
from paddle_billing.Resources.CustomerPortalSessions.Operations import (
    CreateCustomerPortalSession,
)
from paddle_billing.Resources.Subscriptions.Operations import CancelSubscription
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories.paddle_webhook_event_repository import PaddleWebhookEventRepository
from app.repositories.user_repository import UserRepository
from app.services.plan_config import get_plan

logger = logging.getLogger(__name__)


class _WebhookRequest:
    def __init__(self, body: bytes, headers: dict | None = None):
        self._body = body
        self._headers = headers or {}

    @property
    def body(self) -> bytes | None:
        return self._body

    @property
    def content(self) -> bytes | None:
        return self._body

    @property
    def data(self) -> bytes | None:
        return self._body

    @property
    def headers(self) -> dict:
        return self._headers


class PaddleService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    @staticmethod
    def _get_client() -> Client | None:
        if not settings.PADDLE_API_KEY:
            logger.warning("PADDLE_API_KEY no configurado; operaciones de billing deshabilitadas")
            return None
        environment = (
            Environment.SANDBOX
            if settings.PADDLE_ENVIRONMENT == "sandbox"
            else Environment.PRODUCTION
        )
        return Client(api_key=settings.PADDLE_API_KEY, options=Options(environment=environment))

    @staticmethod
    async def create_portal_url(customer_id: str) -> str | None:
        """Create a Paddle customer portal session and return the general URL."""
        client = PaddleService._get_client()
        if not client:
            return None
        try:
            session = await asyncio.to_thread(
                client.customer_portal_sessions.create,
                customer_id,
                CreateCustomerPortalSession(),
            )
            return session.urls.general.url
        except Exception:
            logger.exception("Error creando sesión del customer portal para %s", customer_id)
            return None

    @staticmethod
    async def cancel_subscription(subscription_id: str) -> None:
        """Cancel a Paddle subscription. Best-effort; failures are logged, not raised."""
        client = PaddleService._get_client()
        if not client:
            return
        try:
            await asyncio.to_thread(
                client.subscriptions.cancel,
                subscription_id,
                CancelSubscription(),
            )
            logger.info("Suscripción Paddle %s cancelada", subscription_id)
        except Exception:
            logger.exception(
                "No se pudo cancelar la suscripción Paddle %s en el dashboard; "
                "cancelar manualmente.",
                subscription_id,
            )

    @staticmethod
    def verify_signature(payload: bytes, paddle_signature: str) -> bool:
        if not settings.PADDLE_WEBHOOK_SECRET or not paddle_signature:
            return False

        try:
            secret = Secret(settings.PADDLE_WEBHOOK_SECRET)
            verifier = Verifier()
            request = _WebhookRequest(
                payload,
                headers={"Paddle-Signature": paddle_signature},
            )
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

        if event_id and await _is_duplicate_event(event_id, event_type, event):
            logger.info("Duplicate Paddle event ignored: %s (id=%s)", event_type, event_id)
            return

        logger.info("Paddle webhook received: %s", event_type)

        if event_type == "subscription.created":
            await PaddleService._handle_subscription_created(data)
        elif event_type == "subscription.updated":
            await PaddleService._handle_subscription_updated(data)
        elif event_type == "subscription.canceled":
            await PaddleService._handle_subscription_cancelled(data)
        elif event_type == "subscription.paused":
            await PaddleService._handle_subscription_paused(data)
        elif event_type == "subscription.activated":
            await PaddleService._handle_subscription_activated(data)
        elif event_type in ("transaction.completed", "transaction.paid"):
            await PaddleService._handle_transaction_completed(data)
        else:
            logger.debug("Unhandled Paddle event: %s", event_type)

    @staticmethod
    async def _handle_subscription_created(data: dict) -> None:
        custom_data = data.get("custom_data") or {}
        if not isinstance(custom_data, dict):
            custom_data = {}
        user_id = custom_data.get("user_id")

        paddle_customer_id = str(data.get("customer_id", ""))
        paddle_subscription_id = str(data.get("id", ""))
        status = data.get("status", "active")

        if not user_id:
            logger.warning("subscription.created missing user_id in custom_data")
            return

        items = data.get("items", [])
        if not items:
            logger.warning("subscription.created sin items para %s", paddle_subscription_id)
            return
        price_id = items[0].get("price", {}).get("id", "")
        plan_name = _price_to_plan(price_id)
        if plan_name is None:
            logger.warning(
                "Paddle price_id %s no matchea ningún plan en subscription.created. "
                "Ignorando evento (no se degrada al plan free).",
                price_id,
            )
            return

        from app.database import async_session_factory

        async with async_session_factory() as db:
            repo = UserRepository(db)
            try:
                user = await repo.get_by_id(UUID(user_id))
            except ValueError:
                logger.warning("subscription.created: user_id inválido %s", user_id)
                return
            if not user:
                logger.warning("subscription.created: user %s not found", user_id)
                return

            customer = data.get("customer") or {}
            customer_email = (customer.get("email") or "").lower()
            if customer_email and customer_email != user.email.lower():
                logger.warning(
                    "subscription.created: email del customer %s no coincide con el usuario %s",
                    customer_email, user.id,
                )
                return

            if user.paddle_customer_id and user.paddle_customer_id != paddle_customer_id:
                logger.warning(
                    "subscription.created: customer %s no coincide con el usuario %s",
                    paddle_customer_id, user_id,
                )
                return

            plan = get_plan(plan_name)
            now = datetime.now(UTC)

            user.subscription_plan = plan_name
            user.subscription_status = _map_paddle_status(status)
            user.conversions_limit = plan.conversions_limit
            user.storage_limit = plan.storage_limit
            user.priority_processing = plan.priority_processing
            user.paddle_customer_id = paddle_customer_id or user.paddle_customer_id
            user.paddle_subscription_id = paddle_subscription_id
            user.conversions_used = 0
            user.conversions_reset_at = now
            user.subscription_end = _parse_subscription_end(data)

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

            plan_name = _price_to_plan(price_id)
            if plan_name is None:
                logger.warning(
                    "Paddle price_id %s no matchea ningún plan en subscription.updated. "
                    "Manteniendo plan actual (%s).",
                    price_id, user.subscription_plan,
                )

            mapped_status = _map_paddle_status(status)
            if mapped_status == "canceled":
                _apply_free_plan(user)
            elif plan_name is not None:
                plan = get_plan(plan_name)
                user.subscription_plan = plan_name
                user.subscription_status = mapped_status
                user.conversions_limit = plan.conversions_limit
                user.storage_limit = plan.storage_limit
                user.priority_processing = plan.priority_processing
                new_end = _parse_subscription_end(data)
                if new_end is not None:
                    user.subscription_end = new_end

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

            _apply_free_plan(user)
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
    async def _handle_subscription_activated(data: dict) -> None:
        paddle_subscription_id = data.get("id", "")

        from app.database import async_session_factory

        async with async_session_factory() as db:
            repo = UserRepository(db)
            user = await repo.get_by_paddle_subscription(str(paddle_subscription_id))
            if not user:
                return

            user.subscription_status = "active"
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

            items = data.get("items", [])
            if not items:
                return

            price_id = items[0].get("price", {}).get("id", "")
            plan_name = _price_to_plan(price_id)
            if plan_name is None:
                logger.warning(
                    "Paddle price_id %s no matchea ningún plan en transaction.completed. "
                    "Manteniendo plan actual (%s).",
                    price_id, user.subscription_plan,
                )
            else:
                plan = get_plan(plan_name)
                user.subscription_plan = plan_name
                user.conversions_limit = plan.conversions_limit
                user.storage_limit = plan.storage_limit
                user.priority_processing = plan.priority_processing

            if user.subscription_status == "canceled":
                await db.commit()
                return

            billing_period = items[0].get("billing_period") or {}
            period_end = billing_period.get("ends_at")
            if period_end:
                user.subscription_end = datetime.fromisoformat(
                    period_end.replace("Z", "+00:00")
                )

            now = datetime.now(UTC)
            user.subscription_status = "active"
            user.conversions_used = 0
            user.conversions_reset_at = now

            await repo._save(user)
            await db.commit()


def _price_to_plan(price_id: str) -> str | None:
    mapping = {
        settings.PADDLE_PRICE_STARTER: "starter",
        settings.PADDLE_PRICE_PRO: "pro",
        settings.PADDLE_PRICE_BUSINESS: "business",
    }
    if not price_id:
        return None
    return mapping.get(price_id)


def _apply_free_plan(user) -> None:
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


def _parse_subscription_end(data: dict) -> datetime | None:
    next_period = data.get("next_billing_period") or {}
    if isinstance(next_period, dict):
        end = next_period.get("ends_at")
        if end:
            return datetime.fromisoformat(end.replace("Z", "+00:00"))

    next_transaction = data.get("next_transaction") or {}
    if isinstance(next_transaction, dict):
        period = next_transaction.get("billing_period") or {}
        end = period.get("ends_at")
        if end:
            return datetime.fromisoformat(end.replace("Z", "+00:00"))

    renewal_date = data.get("renewal_date")
    if renewal_date:
        return datetime.fromisoformat(renewal_date.replace("Z", "+00:00"))
    return None


async def _is_duplicate_event(event_id: str, event_type: str, event: dict) -> bool:
    """Persist webhook events in the DB so dedup survives restarts and multi-worker.

    Returns True when the event was already processed. The unique index on
    ``event_id`` guards against concurrent delivery across uvicorn workers.
    """
    from app.database import async_session_factory

    async with async_session_factory() as db:
        repo = PaddleWebhookEventRepository(db)
        existing = await repo.get_by_event_id(event_id)
        if existing:
            return True
        try:
            await repo.create(event_id, event_type, event)
            await db.commit()
            return False
        except IntegrityError:
            await db.rollback()
            return True


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
