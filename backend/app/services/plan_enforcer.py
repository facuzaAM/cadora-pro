from datetime import UTC, datetime

from fastapi import Depends, HTTPException
from sqlalchemy import or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_402_PAYMENT_REQUIRED, HTTP_403_FORBIDDEN

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.plan_config import get_plan
from app.utils.dependencies import get_current_user


async def _degrade_if_past_due(user: User, db: AsyncSession) -> None:
    """When a Paddle subscription is past_due, drop the user back to the free
    plan so they can't keep consuming paid-tier resources without paying.
    """
    if user.subscription_plan == "free" or user.subscription_status != "past_due":
        return

    free_plan = get_plan("free")
    now = datetime.now(UTC)
    user.subscription_plan = "free"
    user.conversions_limit = free_plan.conversions_limit
    user.storage_limit = free_plan.storage_limit
    user.priority_processing = free_plan.priority_processing
    user.conversions_used = 0
    user.conversions_reset_at = now
    user.subscription_end = None

    repo = UserRepository(db)
    await repo._save(user)


async def enforce_conversion_limit(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    if settings.ENVIRONMENT == "production" and not user.email_verified:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Verificá tu email antes de usar el servicio. "
                   "Revisá tu bandeja de entrada o solicitá un nuevo código.",
        )
    await _degrade_if_past_due(user, db)
    if _maybe_reset_monthly(user):
        repo = UserRepository(db)
        await repo._save(user)
    if user.conversions_limit > 0 and user.conversions_used >= user.conversions_limit:
        raise HTTPException(
            status_code=HTTP_402_PAYMENT_REQUIRED,
            detail="Has alcanzado el límite de conversiones de tu plan. "
                   "Actualiza tu plan para seguir usando el servicio.",
        )
    return user


async def consume_conversion(db: AsyncSession, user_id) -> bool:
    """Atomically increment conversions_used only if the plan limit allows it.

    Returns False when the limit was already reached (guards against
    check-then-act races under concurrent requests).
    """
    result = await db.execute(
        update(User)
        .where(
            User.id == user_id,
            or_(User.conversions_limit == 0, User.conversions_used < User.conversions_limit),
        )
        .values(conversions_used=User.conversions_used + 1)
    )
    await db.commit()
    return result.rowcount == 1  # type: ignore[attr-defined]


def _maybe_reset_monthly(user: User) -> bool:
    """Reset conversions_used when a new billing month starts.

    For free users: resets on the 1st of each month (UTC).
    For paid users: resets when the Paddle billing period renews
    (handled by the transaction.completed webhook via conversions_reset_at).
    Returns True if the user was modified.
    """
    now = datetime.now(UTC)

    if user.conversions_reset_at is None:
        user.conversions_reset_at = now
        return True

    should_reset = False
    if user.subscription_plan == "free":
        last = user.conversions_reset_at
        if last.year != now.year or last.month != now.month:
            should_reset = True
    else:
        if user.subscription_end and now > user.subscription_end:
            should_reset = True

    if should_reset:
        user.conversions_used = 0
        user.conversions_reset_at = now
        return True
    return False


async def check_storage_limit(
    user: User,
    file_size: int,
) -> None:
    if user.storage_limit > 0 and (user.storage_used + file_size) > user.storage_limit:
        raise HTTPException(
            status_code=HTTP_402_PAYMENT_REQUIRED,
            detail="Has alcanzado el límite de almacenamiento de tu plan. "
                   "Actualiza tu plan para subir archivos más grandes.",
        )
