from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

import stripe
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.plan_config import PLANS, get_plan

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def create_checkout_session(
        self, user: User, plan_name: str,
    ) -> str:
        plan = get_plan(plan_name)
        price_id = getattr(settings, plan.stripe_price_key, "")

        if not price_id:
            raise ValueError(f"No Stripe price ID configured for plan: {plan_name}")

        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.name,
                metadata={"user_id": str(user.id)},
            )
            user.stripe_customer_id = customer.id
            await self.repo._save(user)

        session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=settings.STRIPE_SUCCESS_URL,
            cancel_url=settings.STRIPE_CANCEL_URL,
            metadata={"user_id": str(user.id), "plan": plan_name},
        )
        return session.url

    async def create_portal_session(self, user: User) -> str:
        if not user.stripe_customer_id:
            raise ValueError("User has no Stripe customer")
        session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=settings.STRIPE_CANCEL_URL,
        )
        return session.url

    @staticmethod
    async def handle_webhook(payload: bytes, sig_header: str) -> None:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET,
        )

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            await StripeService._handle_checkout_completed(session)

        elif event["type"] == "customer.subscription.updated":
            subscription = event["data"]["object"]
            await StripeService._handle_subscription_updated(subscription)

        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            await StripeService._handle_subscription_deleted(subscription)

        elif event["type"] == "invoice.paid":
            invoice = event["data"]["object"]
            await StripeService._handle_invoice_paid(invoice)

    @staticmethod
    async def _handle_checkout_completed(session: dict) -> None:
        user_id = session.get("metadata", {}).get("user_id")
        plan_name = session.get("metadata", {}).get("plan", "free")
        if not user_id:
            return

        from app.database import async_session_factory
        from app.repositories.user_repository import UserRepository

        async with async_session_factory() as db:
            repo = UserRepository(db)
            user = await repo.get_by_id(UUID(user_id))
            if not user:
                return

            plan = get_plan(plan_name)
            now = datetime.now(timezone.utc)

            user.subscription_plan = plan_name
            user.subscription_status = "active"
            user.conversions_limit = plan.conversions_limit
            user.storage_limit = plan.storage_limit
            user.priority_processing = plan.priority_processing
            user.stripe_customer_id = session.get("customer", user.stripe_customer_id)
            user.conversions_used = 0
            user.conversions_reset_at = now

            period_end = session.get("subscription_details", {}).get("expires_at")
            if not period_end:
                period_end = session.get("expires_at")
            user.subscription_end = (
                datetime.fromtimestamp(period_end, tz=timezone.utc)
                if period_end
                else None
            )

            await repo._save(user)
            await db.commit()

    @staticmethod
    async def _handle_subscription_updated(subscription: dict) -> None:
        customer_id = subscription.get("customer")
        status = subscription.get("status", "inactive")
        current_period_end = subscription.get("current_period_end", 0)
        items = subscription.get("items", {}).get("data", [])
        price_id = items[0]["price"]["id"] if items else ""

        plan_name = "free"
        for name, p in PLANS.items():
            if getattr(settings, p.stripe_price_key, "") == price_id:
                plan_name = name
                break
        else:
            logger.warning(
                "Stripe price_id %s no matchea ningun plan configurado. "
                "Degradando a 'free' para customer %s",
                price_id, customer_id,
            )

        from app.database import async_session_factory
        from app.repositories.user_repository import UserRepository

        async with async_session_factory() as db:
            repo = UserRepository(db)
            user = await repo.get_by_stripe_customer(customer_id)
            if not user:
                return

            plan = get_plan(plan_name)
            user.subscription_plan = plan_name
            user.subscription_status = status
            user.conversions_limit = plan.conversions_limit
            user.storage_limit = plan.storage_limit
            user.priority_processing = plan.priority_processing
            user.subscription_end = (
                datetime.fromtimestamp(current_period_end, tz=timezone.utc)
                if current_period_end
                else None
            )
            await repo._save(user)
            await db.commit()

    @staticmethod
    async def _handle_subscription_deleted(subscription: dict) -> None:
        customer_id = subscription.get("customer")
        from app.database import async_session_factory
        from app.repositories.user_repository import UserRepository

        async with async_session_factory() as db:
            repo = UserRepository(db)
            user = await repo.get_by_stripe_customer(customer_id)
            if not user:
                return

            now = datetime.now(timezone.utc)
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
    async def _handle_invoice_paid(invoice: dict) -> None:
        customer_id = invoice.get("customer")
        subscription_id = invoice.get("subscription")
        if not customer_id:
            return

        from app.database import async_session_factory
        from app.repositories.user_repository import UserRepository

        async with async_session_factory() as db:
            repo = UserRepository(db)
            user = await repo.get_by_stripe_customer(customer_id)
            if not user:
                return

            now = datetime.now(timezone.utc)
            user.subscription_status = "active"
            user.conversions_used = 0
            user.conversions_reset_at = now

            period_end = invoice.get("lines", {}).get("data", [{}])[0].get("period", {}).get("end")
            if period_end:
                user.subscription_end = datetime.fromtimestamp(period_end, tz=timezone.utc)

            await repo._save(user)
            await db.commit()
