import asyncio
import logging
import os
import tempfile
import uuid as _uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_402_PAYMENT_REQUIRED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
)

from app.cad.generator import CadGenerator, convert_dxf_to_dwg
from app.cad.schemas import CadGenerateRequest, CadGenerateResponse
from app.config import settings
from app.database import get_db
from app.detection.pipeline import (
    load_detection,
    run_full_pipeline,
    run_ocr_only,
    serialize_detection,
)
from app.detection.schemas import (
    DoorDetectionResult,
    LineDetectionResult,
    WindowDetectionResult,
)
from app.detection.service import DetectionService
from app.editor.builder import build_detection_results
from app.editor.schemas import ElementsPayload
from app.models.user import User
from app.ocr.schemas import OcrResult
from app.ocr.service import OcrService
from app.repositories.document_repository import DocumentRepository
from app.repositories.project_repository import ProjectRepository
from app.services.plan_config import get_plan
from app.services.plan_enforcer import consume_conversion, enforce_conversion_limit
from app.services.storage_service import StorageService
from app.utils.dependencies import get_current_user
from app.utils.rate_limit import rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()
detection_service = DetectionService()
ocr_service = OcrService()
storage = StorageService()

CAD_CACHE_DIR = "cad/generated"


async def _download_doc_to_temp(
    user_id: UUID, project_id: UUID, doc, prefix: str = "cad"
) -> str:
    """Download a document to a safe temp file and return its path."""
    safe_name = os.path.basename(doc.filename).replace("/", "").replace("\\", "")
    tag = _uuid.uuid4().hex[:8]
    fd, path = tempfile.mkstemp(
        suffix=f"_{safe_name}", prefix=f"{user_id}_{project_id}_{prefix}_{tag}_"
    )
    os.close(fd)
    try:
        content = await storage.download_bytes(
            settings.STORAGE_BUCKET, doc.storage_path,
        )
        with open(path, "wb") as f:
            f.write(content)
    except Exception:
        if os.path.exists(path):
            os.remove(path)
        raise
    return path


def _generate_dxf_sync(
    output_path: str,
    lines_result: LineDetectionResult,
    doors_result: DoorDetectionResult,
    windows_result: WindowDetectionResult,
    ocr_result: OcrResult,
) -> None:
    generator = CadGenerator()
    generator.generate(
        lines_result=lines_result,
        doors_result=doors_result,
        windows_result=windows_result,
        ocr_result=ocr_result,
        output_path=output_path,
    )


def _cad_cache_path(project_id: UUID, fmt: str) -> str:
    ext = "dwg" if fmt == "dwg" else "dxf"
    return f"{CAD_CACHE_DIR}/{project_id}/cadora.{ext}"


def _get_user_format(user: User, requested_format: str) -> str:
    """Validate and resolve the requested format against the user's plan."""
    plan = get_plan(user.subscription_plan)
    if requested_format == "dwg" and not plan.dwg_enabled:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="La exportación DWG requiere un plan Pro o Business.",
        )
    return requested_format


async def _resolve_pipeline(
    project,
    edited_elements,
    temp_paths: list[str],
) -> tuple[LineDetectionResult, DoorDetectionResult, WindowDetectionResult, OcrResult]:
    """Pick the fastest detection data source for DXF generation.

    Priority:
      1. Edited elements (from the online editor) + OCR only.
      2. Cached detection result + OCR only.
      3. Full detection pipeline (first generation).
    """
    cached = project.detection_result

    if edited_elements is not None:
        if cached:
            image_w = cached.get("image_width", 0)
            image_h = cached.get("image_height", 0)
            ocr_result = await run_ocr_only(temp_paths, ocr_service)
        else:
            lines_result, _, _, ocr_result = await run_full_pipeline(
                temp_paths, detection_service, ocr_service,
            )
            image_w = lines_result.image_width
            image_h = lines_result.image_height
        return (
            *build_detection_results(edited_elements, image_w, image_h),
            ocr_result,
        )

    if cached:
        lines_result, doors_result, windows_result = load_detection(cached)
        ocr_result = await run_ocr_only(temp_paths, ocr_service)
        return lines_result, doors_result, windows_result, ocr_result

    return await run_full_pipeline(temp_paths, detection_service, ocr_service)


@router.post("/generate/{project_id}", response_model=CadGenerateResponse)
@rate_limit(settings.RATE_LIMIT_CAD)
async def generate_cad(
    request: Request,
    project_id: UUID,
    body: CadGenerateRequest = CadGenerateRequest(),
    user: User = Depends(enforce_conversion_limit),
    db: AsyncSession = Depends(get_db),
):
    """Run full detection pipeline and generate a DXF/DWG file."""
    fmt = _get_user_format(user, body.format)

    project_repo = ProjectRepository(db)
    project = await project_repo.get_by_id(project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")

    ext = "dwg" if fmt == "dwg" else "dxf"
    cache_key = _cad_cache_path(project_id, fmt)

    if not body.force:
        if project.status == "processing":
            raise HTTPException(
                status_code=HTTP_409_CONFLICT,
                detail="El proyecto ya está siendo procesado.",
            )
        if project.status == "cad_generated":
            size = await storage.get_size(settings.STORAGE_BUCKET, cache_key)
            if size is not None:
                return CadGenerateResponse(
                    filename=f"cadora_{project_id}.{ext}",
                    file_size=size,
                )

    doc_repo = DocumentRepository(db)
    docs = await doc_repo.list_by_project(project_id)
    if not docs:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="El proyecto no tiene documentos. Suba un plano primero.",
        )

    elements = body.elements
    if elements is None and project.edited_elements:
        elements = ElementsPayload.model_validate(project.edited_elements)
    if elements is not None:
        await project_repo.set_edited_elements(project_id, elements.model_dump(mode="json"))

    await project_repo.update_status(project_id, "processing")

    temp_paths = []
    output_path = ""
    try:
        for doc in docs:
            path = await _download_doc_to_temp(user.id, project_id, doc)
            temp_paths.append(path)

        lines_result, doors_result, windows_result, ocr_result = (
            await _resolve_pipeline(project, elements, temp_paths)
        )

        tag = _uuid.uuid4().hex[:8]
        fd, output_path = tempfile.mkstemp(
            suffix=".dxf", prefix=f"{user.id}_{project_id}_cadora_{tag}_"
        )
        os.close(fd)

        await asyncio.to_thread(
            _generate_dxf_sync,
            output_path, lines_result, doors_result, windows_result, ocr_result,
        )

        final_path = output_path
        ext = "dxf"
        if fmt == "dwg":
            dwg_path = output_path.replace(".dxf", ".dwg")
            converted = await asyncio.to_thread(
                convert_dxf_to_dwg, Path(output_path), Path(dwg_path),
            )
            if converted:
                final_path = dwg_path
                ext = "dwg"
            else:
                logger.warning("DWG conversion unavailable, falling back to DXF")
                fmt = "dxf"

        file_size = os.path.getsize(final_path)

        with open(final_path, "rb") as f:
            file_bytes = f.read()

        cache_key = _cad_cache_path(project_id, ext)
        content_type = "application/dwg" if ext == "dwg" else "application/dxf"
        await storage.upload(
            settings.STORAGE_BUCKET, cache_key, file_bytes,
            content_type=content_type,
        )

        if not await consume_conversion(db, user.id):
            await project_repo.update_status(project_id, "error")
            raise HTTPException(
                status_code=HTTP_402_PAYMENT_REQUIRED,
                detail="Has alcanzado el límite de conversiones de tu plan. "
                       "Actualiza tu plan para seguir usando el servicio.",
            )

        await project_repo.update_status(project_id, "cad_generated")

        return CadGenerateResponse(
            filename=f"cadora_{project_id}.{ext}",
            file_size=file_size,
        )
    except HTTPException:
        await project_repo.update_status(project_id, "error")
        raise
    except Exception:
        logger.exception("Error generando CAD para proyecto %s", project_id)
        await project_repo.update_status(project_id, "error")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Error interno del servidor")
    finally:
        for p in temp_paths:
            if p and os.path.exists(p):
                os.remove(p)
        if output_path and os.path.exists(output_path):
            os.remove(output_path)
        if fmt == "dwg" and output_path:
            dwg_temp = output_path.replace(".dxf", ".dwg")
            if os.path.exists(dwg_temp):
                os.remove(dwg_temp)


@router.get("/download/{project_id}")
@rate_limit(settings.RATE_LIMIT_CAD)
async def download_cad(
    request: Request,
    background_tasks: BackgroundTasks,
    project_id: UUID,
    format: str = "dxf",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download the generated DXF/DWG for a project from the cache.

    Read-only: only serves files previously generated via POST /cad/generate.
    """
    fmt = _get_user_format(user, format)

    project_repo = ProjectRepository(db)
    project = await project_repo.get_by_id(project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")

    ext = "dwg" if fmt == "dwg" else "dxf"
    content_type = "application/dwg" if fmt == "dwg" else "application/dxf"
    cache_key = _cad_cache_path(project_id, fmt)

    if not await storage.exists(settings.STORAGE_BUCKET, cache_key):
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"El archivo {ext.upper()} aún no fue generado. "
                   f"Generalo primero desde el proyecto.",
        )

    file_bytes = await storage.download_bytes(settings.STORAGE_BUCKET, cache_key)
    fd, tmp = tempfile.mkstemp(suffix=f".{ext}", prefix=f"dl_{project_id}_")
    os.close(fd)
    with open(tmp, "wb") as f:
        f.write(file_bytes)

    def _cleanup(path: str) -> None:
        if os.path.exists(path):
            os.remove(path)

    background_tasks.add_task(_cleanup, tmp)
    return FileResponse(
        path=tmp,
        filename=f"cadora_{project_id}.{ext}",
        media_type=content_type,
    )
