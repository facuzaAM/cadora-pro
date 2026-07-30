import logging
import os
import tempfile
import uuid as _uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_413_CONTENT_TOO_LARGE

from app.config import settings
from app.database import get_db
from app.detection.schemas import DoorDetectionResult, LineDetectionResult, WindowDetectionResult
from app.detection.service import DetectionService
from app.ocr.schemas import OcrRequest, OcrResult
from app.ocr.service import OcrService
from app.repositories.document_repository import DocumentRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.user_repository import UserRepository
from app.services.plan_enforcer import enforce_conversion_limit
from app.services.storage_service import StorageService
from app.utils.rate_limit import limiter

logger = logging.getLogger(__name__)


def _capture_sentry(exc: Exception | None = None) -> None:
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            sentry_sdk.capture_exception(exc)
        except Exception:
            pass


async def _increment_conversion(user, db: AsyncSession) -> None:
    repo = UserRepository(db)
    user_db = await repo.get_by_id(user.id)
    if user_db:
        user_db.conversions_used += 1
        await repo._save(user_db)


router = APIRouter()
ocr_service = OcrService()
detection_service = DetectionService()
storage = StorageService()


def _safe_temp_path(user_id: UUID, project_id: UUID, filename: str | None, prefix: str = "") -> str:
    """Create a safe temp file path with sanitized filename."""
    safe_name = os.path.basename(filename or "upload").replace("/", "").replace("\\", "")
    tag = _uuid.uuid4().hex[:8]
    suffix = f"_{prefix}" if prefix else ""
    fd, path = tempfile.mkstemp(
        suffix=f"_{safe_name}", prefix=f"{user_id}_{project_id}{suffix}_{tag}_"
    )
    os.close(fd)
    return path


def _validate_upload(file: UploadFile) -> str:
    """Validate file extension and return lowercase extension."""
    if not file.filename:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Archivo no proporcionado")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if f".{ext}" not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Formato .{ext} no soportado",
        )
    return ext


async def _read_upload_safe(file: UploadFile) -> bytes:
    """Read upload file with size limit enforcement."""
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    content = b""
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        content += chunk
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=HTTP_413_CONTENT_TOO_LARGE,
                detail=f"Archivo excede el limite de {settings.MAX_FILE_SIZE_MB}MB",
            )
    return content


@router.post("/ocr/{project_id}", response_model=OcrResult)
@limiter.limit(settings.RATE_LIMIT_DETECTION)
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

    _validate_upload(file)
    content = await _read_upload_safe(file)
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

    await _increment_conversion(user, db)
    return result


@router.post("/ocr/uploaded/{document_id}", response_model=OcrResult)
@limiter.limit(settings.RATE_LIMIT_DETECTION)
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

    await _increment_conversion(user, db)
    return result


@router.post("/windows/{project_id}", response_model=WindowDetectionResult)
@limiter.limit(settings.RATE_LIMIT_DETECTION)
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

    _validate_upload(file)
    content = await _read_upload_safe(file)
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

    await _increment_conversion(user, db)
    return result


@router.post("/lines/{project_id}", response_model=LineDetectionResult)
@limiter.limit(settings.RATE_LIMIT_DETECTION)
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

    _validate_upload(file)
    content = await _read_upload_safe(file)
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

    await _increment_conversion(user, db)
    return result


@router.post("/doors/{project_id}", response_model=DoorDetectionResult)
@limiter.limit(settings.RATE_LIMIT_DETECTION)
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

    _validate_upload(file)
    content = await _read_upload_safe(file)
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

    await _increment_conversion(user, db)
    return result
