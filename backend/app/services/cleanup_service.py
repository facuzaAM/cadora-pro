"""Periodic cleanup service for expired files and tokens.

Runs as a background task during the application lifespan.
- Deletes documents (and their storage files) older than 30 days
- Cleans up expired refresh tokens
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update

from app.config import settings
from app.database import async_session_factory
from app.models.document import Document
from app.models.paddle_event import PaddleWebhookEvent
from app.models.project import Project
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

CLEANUP_INTERVAL_SECONDS = 6 * 60 * 60  # every 6 hours
DOCUMENT_RETENTION_DAYS = 30
PADDLE_EVENT_RETENTION_DAYS = 30


async def _cleanup_old_documents() -> int:
    """Delete documents older than DOCUMENT_RETENTION_DAYS and their storage files.

    Documents belonging to users with an active paid subscription are kept,
    and each deleted document releases its share of storage usage.
    """
    cutoff = datetime.now(UTC) - timedelta(days=DOCUMENT_RETENTION_DAYS)
    storage = StorageService()
    deleted_count = 0

    async with async_session_factory() as session:
        stmt = (
            select(Document, Project, User)
            .join(Project, Document.project_id == Project.id)
            .join(User, Project.user_id == User.id)
            .where(Document.created_at < cutoff)
        )
        result = await session.execute(stmt)
        rows = result.all()

        for doc, project, user in rows:
            if user.subscription_plan != "free" and user.subscription_status == "active":
                continue

            try:
                await storage.delete(settings.STORAGE_BUCKET, doc.storage_path)
            except Exception as e:
                logger.warning("Failed to delete storage file %s: %s", doc.storage_path, e)

            await session.delete(doc)
            await session.execute(
                update(User)
                .where(User.id == project.user_id)
                .values(
                    storage_used=func.greatest(User.storage_used - doc.file_size, 0)
                )
            )
            deleted_count += 1

        if deleted_count > 0:
            await session.commit()
            logger.info(
                "Cleaned up %d old documents (older than %d days)",
                deleted_count, DOCUMENT_RETENTION_DAYS,
            )

    return deleted_count


async def _cleanup_expired_refresh_tokens() -> int:
    """Delete expired refresh tokens."""
    now = datetime.now(UTC)
    deleted_count = 0

    async with async_session_factory() as session:
        stmt = delete(RefreshToken).where(RefreshToken.expires_at < now)
        result = await session.execute(stmt)
        deleted_count = result.rowcount  # type: ignore[attr-defined]
        if deleted_count > 0:
            await session.commit()
            logger.info("Cleaned up %d expired refresh tokens", deleted_count)

    return deleted_count


async def _cleanup_old_paddle_events() -> int:
    """Delete processed Paddle webhook events older than the retention window."""
    cutoff = datetime.now(UTC) - timedelta(days=PADDLE_EVENT_RETENTION_DAYS)
    deleted_count = 0

    async with async_session_factory() as session:
        stmt = delete(PaddleWebhookEvent).where(
            PaddleWebhookEvent.processed_at < cutoff
        )
        result = await session.execute(stmt)
        deleted_count = result.rowcount  # type: ignore[attr-defined]
        if deleted_count > 0:
            await session.commit()
            logger.info("Cleaned up %d old Paddle webhook events", deleted_count)

    return deleted_count


async def _run_cleanup_loop():
    """Background loop that runs cleanup tasks periodically."""
    while True:
        try:
            await _cleanup_old_documents()
            await _cleanup_expired_refresh_tokens()
            await _cleanup_old_paddle_events()
        except Exception:
            logger.exception("Error during cleanup cycle")
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)


async def start_cleanup_task() -> asyncio.Task:
    """Start the cleanup background task. Call this from the app lifespan."""
    task = asyncio.create_task(_run_cleanup_loop())
    logger.info(
        "Started cleanup task (interval=%ds, retention=%d days)",
        CLEANUP_INTERVAL_SECONDS, DOCUMENT_RETENTION_DAYS,
    )
    return task
