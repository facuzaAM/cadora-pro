from uuid import UUID

from sqlalchemy import select

from app.models.user import User
from app.repositories import BaseRepository


class UserRepository(BaseRepository):
    async def create(self, email: str, name: str, hashed_password: str) -> User:
        user = User(email=email, name=name, hashed_password=hashed_password)
        await self._save(user)
        return user

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self._get_by_id(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_paddle_customer(self, customer_id: str) -> User | None:
        stmt = select(User).where(User.paddle_customer_id == customer_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_paddle_subscription(self, subscription_id: str) -> User | None:
        stmt = select(User).where(User.paddle_subscription_id == subscription_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
