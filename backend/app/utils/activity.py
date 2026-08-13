from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.activity_repository import ActivityEventRepository  # noqa: E501


async def log_activity(
    db: AsyncSession, user_id: UUID, project_id: UUID,
    event_type: str, detail: str | None = None,
) -> None:
    repo = ActivityEventRepository(db)
    await repo.create(user_id, project_id, event_type, detail)  # noqa: E501
    await db.commit()
