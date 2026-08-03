from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_413_CONTENT_TOO_LARGE,
)

from app.config import settings
from app.database import get_db
from app.schemas.document import DocumentResponse, UploadResponse
from app.services.document_service import DocumentService
from app.services.plan_enforcer import check_storage_limit, enforce_conversion_limit
from app.utils.dependencies import get_current_user
from app.utils.rate_limit import rate_limit

router = APIRouter()

_MAGIC_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "pdf": (b"%PDF-",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "tiff": (b"II*\x00", b"MM\x00*"),
}


async def _read_upload_safe(file: UploadFile) -> bytes:
    """Read upload file in chunks enforcing the configured size limit."""
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    content = bytearray()
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=HTTP_413_CONTENT_TOO_LARGE,
                detail=f"El archivo excede el límite de {settings.MAX_FILE_SIZE_MB} MB",
            )
    return bytes(content)


def _validate_magic_bytes(file_type: str, content: bytes) -> None:
    """Reject files whose magic bytes do not match their declared extension."""
    signatures = _MAGIC_SIGNATURES.get(file_type)
    if signatures is not None and not any(
        content.startswith(sig) for sig in signatures
    ):
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"El archivo no parece ser un {file_type.upper()} válido",
        )


@router.post("/{project_id}", response_model=UploadResponse, status_code=201)
@rate_limit(settings.RATE_LIMIT_UPLOAD)
async def upload_document(
    request: Request,
    project_id: UUID,
    file: UploadFile,
    user=Depends(enforce_conversion_limit),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Archivo no proporcionado")

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if f".{ext}" not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Formato .{ext} no soportado. Usa: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )

    content = await _read_upload_safe(file)
    _validate_magic_bytes(ext, content)

    await check_storage_limit(user, len(content))

    service = DocumentService(db)
    try:
        return await service.upload(user.id, project_id, file.filename, content)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/{project_id}", response_model=list[DocumentResponse])
async def list_documents(
    project_id: UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    try:
        return await service.list_by_project(user.id, project_id)
    except ValueError:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = DocumentService(db)
    try:
        await service.delete(user.id, document_id)
    except ValueError:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Documento no encontrado")
