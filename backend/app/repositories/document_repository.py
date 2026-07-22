from uuid import UUID

from sqlalchemy import select

from app.models.document import Document
from app.repositories import BaseRepository


class DocumentRepository(BaseRepository):
    async def create(
        self,
        project_id: UUID,
        filename: str,
        file_type: str,
        file_size: int,
        storage_path: str,
    ) -> Document:
        doc = Document(
            project_id=project_id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            storage_path=storage_path,
        )
        await self._save(doc)
        return doc

    async def get_by_id(self, document_id: UUID) -> Document | None:
        return await self._get_by_id(Document, document_id)

    async def list_by_project(self, project_id: UUID) -> list[Document]:
        stmt = (
            select(Document)
            .where(Document.project_id == project_id)
            .order_by(Document.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, document_id: UUID) -> None:
        await self._delete(Document, document_id)
