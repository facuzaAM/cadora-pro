from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.document_repository import DocumentRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.document import DocumentResponse, UploadResponse
from app.services.storage_service import StorageService


class DocumentService:
    def __init__(self, db: AsyncSession):
        self.repo = DocumentRepository(db)
        self.project_repo = ProjectRepository(db)
        self.storage = StorageService()

    async def upload(
        self, user_id: UUID, project_id: UUID, filename: str, file_data: bytes
    ) -> UploadResponse:
        project = await self.project_repo.get_by_id(project_id)
        if not project or project.user_id != user_id:
            raise ValueError("Proyecto no encontrado")

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        file_type = ext
        storage_path = await self.storage.upload(
            bucket="cadora-documents",
            path=f"{user_id}/{project_id}/{filename}",
            data=file_data,
            content_type=f"image/{ext}" if ext != "pdf" else "application/pdf",
        )

        doc = await self.repo.create(
            project_id=project_id,
            filename=filename,
            file_type=file_type,
            file_size=len(file_data),
            storage_path=storage_path,
        )

        # Increment storage usage
        from app.repositories.user_repository import UserRepository
        user_repo = UserRepository(self.repo.db)
        user = await user_repo.get_by_id(user_id)
        if user:
            user.storage_used += len(file_data)
            await user_repo._save(user)

        await self.project_repo.update_status(project_id, "document_uploaded")

        return UploadResponse(
            id=doc.id,
            filename=doc.filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            download_url=storage_path,
            created_at=doc.created_at,
        )

    async def list_by_project(
        self, user_id: UUID, project_id: UUID
    ) -> list[DocumentResponse]:
        project = await self.project_repo.get_by_id(project_id)
        if not project or project.user_id != user_id:
            raise ValueError("Proyecto no encontrado")
        docs = await self.repo.list_by_project(project_id)
        return [DocumentResponse.model_validate(d) for d in docs]

    async def delete(self, user_id: UUID, document_id: UUID) -> None:
        doc = await self.repo.get_by_id(document_id)
        if not doc:
            raise ValueError("Documento no encontrado")

        project = await self.project_repo.get_by_id(doc.project_id)
        if not project or project.user_id != user_id:
            raise ValueError("Documento no encontrado")

        await self.storage.delete("cadora-documents", doc.storage_path)
        await self.repo.delete(document_id)

        # Decrement storage usage
        from app.repositories.user_repository import UserRepository
        user_repo = UserRepository(self.repo.db)
        user = await user_repo.get_by_id(user_id)
        if user:
            user.storage_used = max(0, user.storage_used - doc.file_size)
            await user_repo._save(user)
