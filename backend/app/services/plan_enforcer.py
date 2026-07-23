from datetime import UTC, datetime

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_402_PAYMENT_REQUIRED, HTTP_403_FORBIDDEN

from app.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utils.dependencies import get_current_user


async def enforce_conversion_limit(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
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


def _maybe_reset_monthly(user: User) -> bool:
    """Reset conversions_used when a new billing month starts.

    For free users: resets on the 1st of each month (UTC).
    For paid users: resets when the Stripe billing period renews
    (handled by the invoice.paid webhook via conversions_reset_at).
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


async def require_priority_processing(
    user: User = Depends(get_current_user),
) -> User:
    if not user.priority_processing:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="El procesamiento prioritario requiere un plan Pro o Business.",
        )
    return user
