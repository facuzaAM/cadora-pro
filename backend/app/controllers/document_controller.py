from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND

from app.config import settings
from app.database import get_db
from app.schemas.document import DocumentResponse, UploadResponse
from app.services.document_service import DocumentService
from app.services.plan_enforcer import enforce_conversion_limit, check_storage_limit
from app.utils.dependencies import get_current_user
from app.utils.rate_limit import limiter

router = APIRouter()


@router.post("/{project_id}", response_model=UploadResponse, status_code=201)
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
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

    content = await file.read()
    if len(content) > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"El archivo excede el límite de {settings.MAX_FILE_SIZE_MB} MB",
        )

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
