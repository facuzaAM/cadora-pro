from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _save(self, instance) -> None:
        self.db.add(instance)
        await self.db.flush()

    async def _delete(self, model_class, id: UUID) -> None:
        stmt = delete(model_class).where(model_class.id == id)
        await self.db.execute(stmt)

    async def _get_by_id(self, model_class, id: UUID):
        stmt = select(model_class).where(model_class.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _update(self, model_class, id: UUID, **values) -> None:
        stmt = update(model_class).where(model_class.id == id).values(**values)
        await self.db.execute(stmt)
