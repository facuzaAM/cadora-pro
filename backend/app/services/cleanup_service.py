"""Periodic cleanup service for expired files and tokens.

Runs as a background task during the application lifespan.
- Deletes documents (and their storage files) older than 30 days
- Cleans up expired refresh tokens
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.database import async_session_factory
from app.models.document import Document
from app.models.refresh_token import RefreshToken
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

CLEANUP_INTERVAL_SECONDS = 6 * 60 * 60  # every 6 hours
DOCUMENT_RETENTION_DAYS = 30


async def _cleanup_old_documents() -> int:
    """Delete documents older than DOCUMENT_RETENTION_DAYS and their storage files."""
    cutoff = datetime.now(UTC) - timedelta(days=DOCUMENT_RETENTION_DAYS)
    storage = StorageService()
    deleted_count = 0

    async with async_session_factory() as session:
        stmt = select(Document).where(Document.created_at < cutoff)
        result = await session.execute(stmt)
        docs = list(result.scalars().all())

        for doc in docs:
            try:
                await storage.delete("cadora-documents", doc.storage_path)
            except Exception as e:
                logger.warning("Failed to delete storage file %s: %s", doc.storage_path, e)

            await session.delete(doc)
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
        deleted_count = result.rowcount
        if deleted_count > 0:
            await session.commit()
            logger.info("Cleaned up %d expired refresh tokens", deleted_count)

    return deleted_count


async def _run_cleanup_loop():
    """Background loop that runs cleanup tasks periodically."""
    while True:
        try:
            await _cleanup_old_documents()
            await _cleanup_expired_refresh_tokens()
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
