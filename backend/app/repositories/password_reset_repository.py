from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.models.password_reset import PasswordResetToken
from app.repositories import BaseRepository


class PasswordResetRepository(BaseRepository):
    async def create(self, user_id: UUID, code: str, expires_at: datetime) -> PasswordResetToken:
        token = PasswordResetToken(
            user_id=user_id,
            code=code,
            expires_at=expires_at,
        )
        await self._save(token)
        return token

    async def get_valid_code(self, code: str) -> PasswordResetToken | None:
        now = datetime.now(UTC)
        stmt = (
            select(PasswordResetToken)
            .where(
                PasswordResetToken.code == code,
                PasswordResetToken.used == False,  # noqa: E712
                PasswordResetToken.expires_at > now,
            )
            .order_by(PasswordResetToken.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_used(self, token_id: UUID) -> None:
        await self._update(PasswordResetToken, token_id, used=True)

    async def invalidate_all_for_user(self, user_id: UUID) -> None:
        stmt = (
            select(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used == False,  # noqa: E712
            )
        )
        result = await self.db.execute(stmt)
        tokens = result.scalars().all()
        for t in tokens:
            await self._update(PasswordResetToken, t.id, used=True)
