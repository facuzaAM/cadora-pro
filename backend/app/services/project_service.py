from contextlib import suppress
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories.document_repository import DocumentRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreateRequest, ProjectResponse, ProjectUpdateRequest
from app.services.storage_service import StorageService


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.repo = ProjectRepository(db)
        self.document_repo = DocumentRepository(db)
        self.storage = StorageService()

    async def create(self, user_id: UUID, request: ProjectCreateRequest) -> ProjectResponse:
        project = await self.repo.create(
            user_id=user_id, name=request.name, description=request.description
        )
        return ProjectResponse.model_validate(project)

    async def get_by_id(self, user_id: UUID, project_id: UUID) -> ProjectResponse:
        project = await self.repo.get_by_id(project_id)
        if not project or project.user_id != user_id:
            raise ValueError("Proyecto no encontrado")
        doc_count = await self.repo.get_document_count(project_id)
        response = ProjectResponse.model_validate(project)
        response.document_count = doc_count
        return response

    async def list_by_user(
        self, user_id: UUID, skip: int = 0, limit: int = 20
    ) -> list[ProjectResponse]:
        projects = await self.repo.list_by_user(user_id, skip=skip, limit=limit)
        counts = await self.repo.get_document_counts([p.id for p in projects])
        return [
            ProjectResponse.model_validate(p).model_copy(
                update={"document_count": counts.get(p.id, 0)}
            )
            for p in projects
        ]

    async def update(
        self, user_id: UUID, project_id: UUID, request: ProjectUpdateRequest
    ) -> ProjectResponse:
        project = await self.repo.get_by_id(project_id)
        if not project or project.user_id != user_id:
            raise ValueError("Proyecto no encontrado")
        updated = await self.repo.update(
            project_id, name=request.name, description=request.description
        )
        return ProjectResponse.model_validate(updated)

    async def delete(self, user_id: UUID, project_id: UUID) -> None:
        project = await self.repo.get_by_id(project_id)
        if not project or project.user_id != user_id:
            raise ValueError("Proyecto no encontrado")

        # Remove stored files so deleting a project does not leak them.
        docs = await self.document_repo.list_by_project(project_id)
        for doc in docs:
            with suppress(Exception):
                await self.storage.delete(settings.STORAGE_BUCKET, doc.storage_path)

        await self.repo.delete(project_id)
