from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_404_NOT_FOUND

from app.database import get_db
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.services.project_service import ProjectService
from app.utils.dependencies import get_current_user

router = APIRouter()


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    return await service.list_by_user(user.id, skip=skip, limit=limit)


@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    request: ProjectCreateRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    return await service.create(user.id, request)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    try:
        return await service.get_by_id(user.id, project_id)
    except ValueError:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    request: ProjectUpdateRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    try:
        return await service.update(user.id, project_id, request)
    except ValueError:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = ProjectService(db)
    try:
        await service.delete(user.id, project_id)
    except ValueError:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
