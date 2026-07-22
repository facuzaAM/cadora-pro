from uuid import UUID

from sqlalchemy import func, select

from app.models.project import Project
from app.repositories import BaseRepository


class ProjectRepository(BaseRepository):
    async def create(
        self, user_id: UUID, name: str, description: str | None = None
    ) -> Project:
        project = Project(user_id=user_id, name=name, description=description)
        await self._save(project)
        return project

    async def get_by_id(self, project_id: UUID) -> Project | None:
        return await self._get_by_id(Project, project_id)

    async def list_by_user(
        self, user_id: UUID, skip: int = 0, limit: int = 20
    ) -> list[Project]:
        stmt = (
            select(Project)
            .where(Project.user_id == user_id)
            .order_by(Project.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_by_user(self, user_id: UUID) -> int:
        stmt = select(func.count()).select_from(Project).where(Project.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def update(
        self, project_id: UUID, name: str | None = None, description: str | None = None
    ) -> Project | None:
        values = {}
        if name is not None:
            values["name"] = name
        if description is not None:
            values["description"] = description
        if values:
            await self._update(Project, project_id, **values)
        return await self.get_by_id(project_id)

    async def update_status(self, project_id: UUID, status: str) -> None:
        await self._update(Project, project_id, status=status)

    async def delete(self, project_id: UUID) -> None:
        await self._delete(Project, project_id)

    async def get_document_count(self, project_id: UUID) -> int:
        from app.models.document import Document

        stmt = (
            select(func.count())
            .select_from(Document)
            .where(Document.project_id == project_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()
