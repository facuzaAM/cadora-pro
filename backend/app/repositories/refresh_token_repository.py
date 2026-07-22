from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from app.models.refresh_token import RefreshToken
from app.repositories import BaseRepository


class RefreshTokenRepository(BaseRepository):
    async def create(self, user_id: UUID, token: str, expires_at: datetime) -> RefreshToken:
        rt = RefreshToken(
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            created_at=datetime.now(timezone.utc),
        )
        await self._save(rt)
        return rt

    async def get_by_token(self, token: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token == token)
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

    async def cleanup_expired(self) -> int:
        now = datetime.now(timezone.utc)
        stmt = select(RefreshToken).where(RefreshToken.expires_at < now)
        result = await self.db.execute(stmt)
        tokens = result.scalars().all()
        for rt in tokens:
            await self.db.delete(rt)
        return len(tokens)
