"""Background detection worker.

Projects in ``detection_running`` state are picked up and processed by a
dedicated polling loop that runs on every uvicorn worker. Jobs are claimed
atomically (``SELECT ... FOR UPDATE SKIP LOCKED`` + status flip) so only one
worker ever processes a given project, even across processes
(``uvicorn --workers N``). A staleness window lets a worker that died
mid-processing be reclaimed and re-run instead of being stuck forever.
"""

import asyncio
import contextlib
import datetime
import logging
import os
import tempfile
import uuid as _uuid
from datetime import UTC
from uuid import UUID

from sqlalchemy import and_, or_, select, update

from app.config import settings
from app.database import async_session_factory
from app.detection.pipeline import run_full_pipeline, serialize_detection
from app.detection.service import DetectionService
from app.models.project import Project
from app.ocr.service import OcrService
from app.repositories.document_repository import DocumentRepository
from app.repositories.project_repository import ProjectRepository
from app.services.plan_enforcer import consume_conversion
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)

# How often the poller scans for pending jobs.
POLL_INTERVAL_SECONDS = 2.0
# A job stuck in detection_processing for longer than this is reclaimed.
STALE_JOB_TIMEOUT_SECONDS = 300
# Heartbeat interval so long-running jobs never look stale.
HEARTBEAT_INTERVAL_SECONDS = 30

detection_service = DetectionService()
ocr_service = OcrService()
storage = StorageService()


async def _claim_pending_project(session) -> tuple[UUID, UUID] | None:
    """Atomically claim one pending job; returns (project_id, user_id)."""
    cutoff = datetime.datetime.now(UTC) - datetime.timedelta(
        seconds=STALE_JOB_TIMEOUT_SECONDS
    )
    stmt = (
        select(Project)
        .where(
            or_(
                Project.status == "detection_running",
                and_(
                    Project.status == "detection_processing",
                    Project.updated_at < cutoff,
                ),
            )
        )
        .with_for_update(skip_locked=True)
        .order_by(Project.updated_at.asc())
        .limit(1)
    )
    project = (await session.execute(stmt)).scalar_one_or_none()
    if project is None:
        return None
    project.status = "detection_processing"
    await session.commit()
    return project.id, project.user_id


async def _process_detection(session, project_id: UUID, user_id: UUID) -> None:
    temp_paths = []
    try:
        doc_repo = DocumentRepository(session)
        docs = await doc_repo.list_by_project(project_id)
        for doc in docs:
            safe_name = os.path.basename(doc.filename).replace("/", "").replace("\\", "")
            tag = _uuid.uuid4().hex[:8]
            fd, path = tempfile.mkstemp(
                suffix=f"_{safe_name}", prefix=f"{user_id}_{project_id}_det_{tag}_"
            )
            os.close(fd)
            content = await storage.download_bytes(
                settings.STORAGE_BUCKET, doc.storage_path,
            )
            with open(path, "wb") as f:
                f.write(content)
            temp_paths.append(path)

        lines_result, doors_result, windows_result, ocr_result = await run_full_pipeline(
            temp_paths, detection_service, ocr_service,
        )
        payload = serialize_detection(
            lines_result, doors_result, windows_result, ocr_result,
        )

        repo = ProjectRepository(session)
        if not await consume_conversion(session, user_id):
            await repo.update_status(project_id, "document_uploaded")
            await session.commit()
            logger.warning(
                "Detección completada pero el usuario %s no tenía conversiones "
                "disponibles (race); proyecto %s vuelto a document_uploaded",
                user_id, project_id,
            )
            return

        await repo.set_detection_result(project_id, payload)
        await repo.update_status(project_id, "detection_completed")
        await session.commit()
    finally:
        for p in temp_paths:
            if p and os.path.exists(p):
                os.remove(p)


async def _process_claimed(project_id: UUID, user_id: UUID) -> None:
    """Process one claimed job with a heartbeat so it is never reclaimed."""
    heartbeat_task = asyncio.create_task(
        _heartbeat(project_id), name=f"det-heartbeat-{project_id}"
    )
    try:
        async with async_session_factory() as session:
            await _process_detection(session, project_id, user_id)
    except Exception:
        logger.exception("Detección falló para proyecto %s", project_id)
        try:
            async with async_session_factory() as session:
                await session.execute(
                    update(Project)
                    .where(
                        and_(
                            Project.id == project_id,
                            Project.status == "detection_processing",
                        )
                    )
                    .values(status="error")
                )
                await session.commit()
        except Exception:
            logger.exception("No se pudo marcar como error el proyecto %s", project_id)
    finally:
        heartbeat_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await heartbeat_task


async def _heartbeat(project_id: UUID) -> None:
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
        try:
            async with async_session_factory() as session:
                await session.execute(
                    update(Project)
                    .where(
                        and_(
                            Project.id == project_id,
                            Project.status == "detection_processing",
                        )
                    )
                    .values(updated_at=datetime.datetime.now(UTC))
                )
                await session.commit()
        except Exception:
            logger.exception("Heartbeat falló para proyecto %s", project_id)


async def _detection_loop() -> None:
    while True:
        try:
            async with async_session_factory() as session:
                claimed = await _claim_pending_project(session)
            if claimed is not None:
                project_id, user_id = claimed
                logger.info("Procesando detección para proyecto %s", project_id)
                await _process_claimed(project_id, user_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Error en el loop de detección")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def start_detection_worker() -> asyncio.Task:
    task = asyncio.create_task(_detection_loop(), name="detection-worker")
    return task
