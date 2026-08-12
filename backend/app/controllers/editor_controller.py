import asyncio
import logging
import os
import tempfile
import uuid as _uuid
from uuid import UUID

import cv2
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_402_PAYMENT_REQUIRED,
    HTTP_404_NOT_FOUND,
)

from app.config import settings
from app.database import get_db
from app.detection.schemas import (
    DoorDetectionResult,
    LineDetectionResult,
    WindowDetectionResult,
)
from app.detection.service import DetectionService
from app.editor.schemas import ElementsPayload
from app.models.user import User
from app.repositories.document_repository import DocumentRepository
from app.repositories.project_repository import ProjectRepository
from app.services.plan_enforcer import prepare_user_for_conversion
from app.services.storage_service import StorageService
from app.utils.dependencies import get_current_user
from app.utils.rate_limit import rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()
storage = StorageService()

PREVIEW_DIR = "previews"


def _preview_key(project_id: UUID) -> str:
    return f"{PREVIEW_DIR}/{project_id}.png"


async def _get_project(user, project_id: UUID, db: AsyncSession):
    repo = ProjectRepository(db)
    project = await repo.get_by_id(project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
    return project


async def _ensure_preview(docs, project_id: UUID) -> bytes:
    """Return the rasterized first-page PNG of the project's plan (cached)."""
    key = _preview_key(project_id)
    if await storage.exists(settings.STORAGE_BUCKET, key):
        return await storage.download_bytes(settings.STORAGE_BUCKET, key)

    doc = docs[0]
    safe_name = os.path.basename(doc.filename).replace("/", "").replace("\\", "")
    tag = _uuid.uuid4().hex[:8]
    fd, path = tempfile.mkstemp(suffix=f"_{safe_name}", prefix=f"preview_{tag}_")
    os.close(fd)
    try:
        content = await storage.download_bytes(settings.STORAGE_BUCKET, doc.storage_path)
        with open(path, "wb") as f:
            f.write(content)

        image = await asyncio.to_thread(DetectionService._load_image_from_file, path)
        ok, buf = cv2.imencode(".png", cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
        if not ok:
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail="No se pudo generar la vista previa",
            )
        data = buf.tobytes()
        await storage.upload(settings.STORAGE_BUCKET, key, data, content_type="image/png")
        return data
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error generando preview para proyecto %s", project_id)
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="No se pudo generar la vista previa",
        )
    finally:
        if os.path.exists(path):
            os.remove(path)


@router.post("/{project_id}/detection/run")
@rate_limit(settings.RATE_LIMIT_DETECTION)
async def run_detection(
    request: Request,
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Queue detection for the background worker (idempotent). Returns status immediately."""
    project = await _get_project(user, project_id, db)

    if project.detection_result is not None:
        return {"status": "completed"}
    if project.status in ("detection_running", "detection_processing"):
        return {"status": "processing"}

    # First detection of the project consumes the plan conversion (charged by
    # the worker). Already-paid projects can re-detect freely.
    if not project.conversion_charged:
        await prepare_user_for_conversion(user, db)
        if user.conversions_limit > 0 and user.conversions_used >= user.conversions_limit:
            raise HTTPException(
                status_code=HTTP_402_PAYMENT_REQUIRED,
                detail="Has alcanzado el límite de conversiones de tu plan. "
                       "Actualiza tu plan para seguir usando el servicio.",
            )

    doc_repo = DocumentRepository(db)
    docs = await doc_repo.list_by_project(project_id)
    if not docs:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="El proyecto no tiene documentos. Suba un plano primero.",
        )

    repo = ProjectRepository(db)
    await repo.update_status(project_id, "detection_running")
    await db.commit()
    return {"status": "processing"}


@router.get("/{project_id}/detection")
@rate_limit(settings.RATE_LIMIT_DETECTION)
async def get_detection(
    request: Request,
    project_id: UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the detection result for the editor, or a status to poll."""
    project = await _get_project(user, project_id, db)

    if project.detection_result is None:
        if project.status == "error":
            return {"status": "error"}
        status = (
            "processing"
            if project.status in ("detection_running", "detection_processing")
            else "pending"
        )
        return {"status": status}

    payload = project.detection_result
    lines_result = LineDetectionResult.model_validate(payload["lines"])
    doors_result = DoorDetectionResult.model_validate(payload["doors"])
    windows_result = WindowDetectionResult.model_validate(payload["windows"])

    walls = [
        {
            "id": str(s.id),
            "x1": s.x1,
            "y1": s.y1,
            "x2": s.x2,
            "y2": s.y2,
        }
        for s in lines_result.grouped_lines
    ]
    doors = [
        {
            "id": str(d.id),
            "type": d.type.value,
            "x": d.x,
            "y": d.y,
            "width": d.width,
            "rotation": d.rotation,
            "swing": d.swing,
            "confidence": d.confidence,
        }
        for d in doors_result.doors
    ]
    windows = [
        {
            "id": str(w.id),
            "type": w.type.value,
            "x": w.x,
            "y": w.y,
            "width": w.width,
            "height": w.height,
            "rotation": w.rotation,
            "confidence": w.confidence,
        }
        for w in windows_result.windows
    ]

    return {
        "status": "completed",
        "walls": walls,
        "doors": doors,
        "windows": windows,
        "arcs": [a.model_dump(mode="json") for a in lines_result.arcs],
        "ocr_texts": payload.get("ocr_texts", []),
        "ocr_measurements": payload.get("ocr_measurements", []),
        "image_width": payload.get("image_width", 0),
        "image_height": payload.get("image_height", 0),
    }


@router.get("/{project_id}/preview/image")
@rate_limit(settings.RATE_LIMIT_DETECTION)
async def preview_image(
    request: Request,
    project_id: UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Serve a rasterized PNG of the plan for the editor canvas."""
    await _get_project(user, project_id, db)

    doc_repo = DocumentRepository(db)
    docs = await doc_repo.list_by_project(project_id)
    if not docs:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="El proyecto no tiene documentos. Suba un plano primero.",
        )

    data = await _ensure_preview(docs, project_id)
    return Response(content=data, media_type="image/png")


@router.put("/{project_id}/elements")
async def save_elements(
    project_id: UUID,
    payload: ElementsPayload,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Persist the edited walls/doors/windows for later export."""
    await _get_project(user, project_id, db)
    repo = ProjectRepository(db)
    await repo.set_edited_elements(project_id, payload.model_dump(mode="json"))
    return {"ok": True}


@router.get("/{project_id}/elements")
async def get_elements(
    project_id: UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the saved edits (walls/doors/windows) or null."""
    project = await _get_project(user, project_id, db)
    return project.edited_elements
