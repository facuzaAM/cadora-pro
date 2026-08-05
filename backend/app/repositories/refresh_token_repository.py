from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.models.refresh_token import RefreshToken
from app.repositories import BaseRepository
from app.utils.tokens import hash_secret


class RefreshTokenRepository(BaseRepository):
    async def create(self, user_id: UUID, token: str, expires_at: datetime) -> RefreshToken:
        rt = RefreshToken(
            user_id=user_id,
            token=hash_secret(token),
            expires_at=expires_at,
            created_at=datetime.now(UTC),
        )
        await self._save(rt)
        return rt

    async def get_by_token(self, token: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token == hash_secret(token))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke(self, token: str) -> None:
        rt = await self.get_by_token(token)
        if rt:
            rt.revoked = True
            self.db.add(rt)

    async def revoke_all_for_user(self, user_id: UUID) -> None:
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        for rt in result.scalars().all():
            rt.revoked = True
            self.db.add(rt)
