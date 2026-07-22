from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreateRequest, ProjectResponse, ProjectUpdateRequest


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.repo = ProjectRepository(db)

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
        result = []
        for p in projects:
            doc_count = await self.repo.get_document_count(p.id)
            r = ProjectResponse.model_validate(p)
            r.document_count = doc_count
            result.append(r)
        return result

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
        await self.repo.delete(project_id)
