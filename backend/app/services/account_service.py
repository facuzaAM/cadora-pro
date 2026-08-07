import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.services.paddle_service import PaddleService
from app.services.storage_service import StorageService
from app.utils.security import verify_password

logger = logging.getLogger(__name__)


class AccountService:
    def __init__(self, db: AsyncSession):
        self.user_repo = UserRepository(db)
        self.project_repo = ProjectRepository(db)
        self.storage = StorageService()

    async def export_user_data(self, user_id: UUID) -> dict:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("Usuario no encontrado")

        projects = await self.project_repo.list_by_user(user_id, skip=0, limit=1000)
        documents = await self.project_repo.list_documents_by_user(user_id)

        docs_by_project: dict[UUID, list[dict]] = {}
        for doc in documents:
            try:
                url = await self.storage.get_download_url(
                    settings.STORAGE_BUCKET, doc.storage_path
                )
            except Exception:
                url = None
            docs_by_project.setdefault(doc.project_id, []).append(
                {
                    "id": str(doc.id),
                    "filename": doc.filename,
                    "file_type": doc.file_type,
                    "file_size": doc.file_size,
                    "download_url": url,
                    "created_at": doc.created_at.isoformat(),
                }
            )

        return {
            "exported_at": datetime.now(UTC).isoformat(),
            "profile": {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "avatar_url": user.avatar_url,
                "email_verified": user.email_verified,
                "created_at": user.created_at.isoformat(),
            },
            "subscription": {
                "plan": user.subscription_plan,
                "status": user.subscription_status,
                "subscription_end": (
                    user.subscription_end.isoformat()
                    if user.subscription_end
                    else None
                ),
                "conversions_used": user.conversions_used,
                "conversions_limit": user.conversions_limit,
                "storage_used": user.storage_used,
                "storage_limit": user.storage_limit,
            },
            "projects": [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "description": p.description,
                    "status": p.status,
                    "created_at": p.created_at.isoformat(),
                    "documents": docs_by_project.get(p.id, []),
                }
                for p in projects
            ],
        }

    async def delete_account(self, user_id: UUID, password: str) -> None:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        if not verify_password(password, user.hashed_password):
            raise ValueError("La contraseña es incorrecta")
        await self._delete_user_cleanup(user)

    async def delete_account_by_admin(self, user_id: UUID) -> None:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        await self._delete_user_cleanup(user)

    async def _delete_user_cleanup(self, user: User) -> None:
        if user.paddle_subscription_id:
            await PaddleService.cancel_subscription(user.paddle_subscription_id)
            logger.info(
                "Suscripción Paddle %s cancelada por borrado de cuenta %s",
                user.paddle_subscription_id, user.id,
            )

        documents = await self.project_repo.list_documents_by_user(user.id)
        for doc in documents:
            try:
                await self.storage.delete(settings.STORAGE_BUCKET, doc.storage_path)
            except Exception:
                logger.warning(
                    "Failed to delete stored file %s for user %s",
                    doc.storage_path, user.id,
                )

        await self.user_repo.delete(user.id)
