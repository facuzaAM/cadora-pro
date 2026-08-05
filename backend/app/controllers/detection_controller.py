import logging
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_402_PAYMENT_REQUIRED, HTTP_404_NOT_FOUND

from app.config import settings
from app.database import get_db
from app.detection.schemas import DoorDetectionResult, LineDetectionResult, WindowDetectionResult
from app.detection.service import DetectionService
from app.ocr.schemas import OcrRequest, OcrResult
from app.ocr.service import OcrService
from app.repositories.document_repository import DocumentRepository
from app.repositories.project_repository import ProjectRepository
from app.services.plan_enforcer import consume_conversion, enforce_conversion_limit
from app.services.storage_service import StorageService
from app.utils.rate_limit import rate_limit
from app.utils.uploads import (
    make_temp_path,
    read_upload_with_limit,
    validate_extension,
    validate_magic_bytes,
)

logger = logging.getLogger(__name__)


def _capture_sentry(exc: Exception | None = None) -> None:
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            sentry_sdk.capture_exception(exc)
        except Exception:
            pass


async def _consume_or_402(user, db: AsyncSession) -> None:
    if not await consume_conversion(db, user.id):
        raise HTTPException(
            status_code=HTTP_402_PAYMENT_REQUIRED,
            detail="Has alcanzado el límite de conversiones de tu plan. "
                   "Actualiza tu plan para seguir usando el servicio.",
        )


router = APIRouter()
ocr_service = OcrService()
detection_service = DetectionService()
storage = StorageService()


def _safe_temp_path(user_id, project_id, filename: str | None, prefix: str = "") -> str:
    """Create a safe temp file path with sanitized filename."""
    label = f"{user_id}_{project_id}"
    if prefix:
        label = f"{label}_{prefix}"
    return make_temp_path(label, filename)


async def _read_upload_safe(file: UploadFile) -> bytes:
    """Read upload file with size limit enforcement."""
    return await read_upload_with_limit(
        file,
        settings.MAX_FILE_SIZE_MB * 1024 * 1024,
        f"Archivo excede el limite de {settings.MAX_FILE_SIZE_MB}MB",
    )


@router.post("/ocr/{project_id}", response_model=OcrResult)
@rate_limit(settings.RATE_LIMIT_DETECTION)
async def ocr_document(
    request: Request,
    project_id: UUID,
    file: UploadFile,
    language: str = "spa+eng",
    user=Depends(enforce_conversion_limit),
    db: AsyncSession = Depends(get_db),
):
    """Run OCR on an uploaded document image/PDF and return classified texts."""
    project_repo = ProjectRepository(db)
    project = await project_repo.get_by_id(project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")

    ext = validate_extension(file, settings.ALLOWED_EXTENSIONS)
    content = await _read_upload_safe(file)
    validate_magic_bytes(ext, content)
    temp_path = _safe_temp_path(user.id, project_id, file.filename)
    try:
        with open(temp_path, "wb") as f:
            f.write(content)

        ocr_request = OcrRequest(language=language)
        result = await ocr_service.process_file(temp_path, request=ocr_request)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error procesando OCR en documento")
        _capture_sentry()
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="No pudimos leer el texto del plano. Verificá que la imagen sea nítida "
                   "y que el archivo no esté dañado. Probá con otro archivo.",
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    await _consume_or_402(user, db)
    return result


@router.post("/ocr/uploaded/{document_id}", response_model=OcrResult)
@rate_limit(settings.RATE_LIMIT_DETECTION)
async def ocr_uploaded_document(
    request: Request,
    document_id: UUID,
    language: str = "spa+eng",
    user=Depends(enforce_conversion_limit),
    db: AsyncSession = Depends(get_db),
):
    """Run OCR on a previously uploaded document."""
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Documento no encontrado")

    project_repo = ProjectRepository(db)
    project = await project_repo.get_by_id(doc.project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Documento no encontrado")

    temp_path = _safe_temp_path(user.id, document_id, doc.filename)
    try:
        content = await storage.download_bytes(
            settings.STORAGE_BUCKET, doc.storage_path,
        )
        with open(temp_path, "wb") as f:
            f.write(content)

        ocr_request = OcrRequest(language=language)
        result = await ocr_service.process_file(temp_path, request=ocr_request)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error procesando OCR en documento subido")
        _capture_sentry()
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="No pudimos leer el texto del plano. Verificá que la imagen sea nítida "
                   "y que el archivo no esté dañado.",
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    await _consume_or_402(user, db)
    return result


@router.post("/windows/{project_id}", response_model=WindowDetectionResult)
@rate_limit(settings.RATE_LIMIT_DETECTION)
async def detect_windows(
    request: Request,
    project_id: UUID,
    file: UploadFile,
    user=Depends(enforce_conversion_limit),
    db: AsyncSession = Depends(get_db),
):
    """Detect windows (sliding, fixed, casement) in a floor plan image."""
    project_repo = ProjectRepository(db)
    project = await project_repo.get_by_id(project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")

    ext = validate_extension(file, settings.ALLOWED_EXTENSIONS)
    content = await _read_upload_safe(file)
    validate_magic_bytes(ext, content)
    temp_path = _safe_temp_path(user.id, project_id, file.filename, prefix="windows")
    try:
        with open(temp_path, "wb") as f:
            f.write(content)

        result = await detection_service.process_file_windows(temp_path)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error detectando ventanas")
        _capture_sentry()
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="No pudimos detectar ventanas en el plano. "
                   "Asegurate de que el archivo sea un plano arquitectónico legible.",
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    await _consume_or_402(user, db)
    return result


@router.post("/lines/{project_id}", response_model=LineDetectionResult)
@rate_limit(settings.RATE_LIMIT_DETECTION)
async def detect_lines(
    request: Request,
    project_id: UUID,
    file: UploadFile,
    user=Depends(enforce_conversion_limit),
    db: AsyncSession = Depends(get_db),
):
    """Detect horizontal, vertical and diagonal lines in a floor plan image."""
    project_repo = ProjectRepository(db)
    project = await project_repo.get_by_id(project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")

    ext = validate_extension(file, settings.ALLOWED_EXTENSIONS)
    content = await _read_upload_safe(file)
    validate_magic_bytes(ext, content)
    temp_path = _safe_temp_path(user.id, project_id, file.filename, prefix="lines")
    try:
        with open(temp_path, "wb") as f:
            f.write(content)

        result = await detection_service.process_file(temp_path)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error detectando lineas")
        _capture_sentry()
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="No pudimos detectar las líneas del plano. "
                   "Probá con un archivo de mayor calidad o resolución.",
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    await _consume_or_402(user, db)
    return result


@router.post("/doors/{project_id}", response_model=DoorDetectionResult)
@rate_limit(settings.RATE_LIMIT_DETECTION)
async def detect_doors(
    request: Request,
    project_id: UUID,
    file: UploadFile,
    user=Depends(enforce_conversion_limit),
    db: AsyncSession = Depends(get_db),
):
    """Detect doors (single, double, sliding) in a floor plan image."""
    project_repo = ProjectRepository(db)
    project = await project_repo.get_by_id(project_id)
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")

    ext = validate_extension(file, settings.ALLOWED_EXTENSIONS)
    content = await _read_upload_safe(file)
    validate_magic_bytes(ext, content)
    temp_path = _safe_temp_path(user.id, project_id, file.filename, prefix="doors")
    try:
        with open(temp_path, "wb") as f:
            f.write(content)

        result = await detection_service.process_file_doors(temp_path)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error detectando puertas")
        _capture_sentry()
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="No pudimos detectar puertas en el plano. "
                   "Asegurate de que el archivo sea un plano arquitectónico legible.",
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    await _consume_or_402(user, db)
    return result
