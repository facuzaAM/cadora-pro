from uuid import UUID

from sqlalchemy import select

from app.models.activity_event import ActivityEvent
from app.repositories import BaseRepository


class ActivityEventRepository(BaseRepository):
    async def create(
        self, user_id: UUID, project_id: UUID,
        event_type: str, detail: str | None = None,
    ) -> ActivityEvent:
        ev = ActivityEvent(
            user_id=user_id, project_id=project_id,
            event_type=event_type, detail=detail)
        self.db.add(ev)
        await self.db.flush()
        return ev

    async def list_by_project(self, project_id: UUID, limit: int = 50):
        stmt = (
            select(ActivityEvent)
            .where(ActivityEvent.project_id == project_id)
            .order_by(ActivityEvent.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
