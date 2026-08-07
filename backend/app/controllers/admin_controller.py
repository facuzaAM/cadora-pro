from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from app.database import get_db
from app.models.project import Project
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.account_service import AccountService
from app.utils.dependencies import get_current_user

router = APIRouter()


async def require_admin(
    user: User = Depends(get_current_user),
) -> User:
    if not user.is_admin:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="Acceso restringido a administradores",
        )
    return user


@router.get("/users")
async def list_users(
    q: str = "",
    skip: int = 0,
    limit: int = 50,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User, func.count(Project.id)).outerjoin(Project).group_by(User.id)
    if q:
        stmt = stmt.where(
            User.email.ilike(f"%{q}%") | User.name.ilike(f"%{q}%")
        )
    stmt = stmt.order_by(User.created_at.desc()).offset(skip).limit(limit)

    rows = (await db.execute(stmt)).all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "name": u.name,
            "is_admin": u.is_admin,
            "email_verified": u.email_verified,
            "subscription_plan": u.subscription_plan,
            "subscription_status": u.subscription_status,
            "conversions_used": u.conversions_used,
            "conversions_limit": u.conversions_limit,
            "storage_used": u.storage_used,
            "storage_limit": u.storage_limit,
            "project_count": count,
            "created_at": u.created_at.isoformat() if u.created_at else "",
        }
        for u, count in rows
    ]


@router.get("/stats")
async def admin_stats(
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    total_users = (await db.execute(select(func.count(User.id)))).scalar_one()
    total_projects = (await db.execute(select(func.count(Project.id)))).scalar_one()
    return {
        "total_users": total_users,
        "total_projects": total_projects,
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    target = await repo.get_by_id(user_id)
    if not target:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if target.is_admin:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail="No se puede eliminar un administrador",
        )
    service = AccountService(db)
    await service.delete_account_by_admin(user_id)
    return {"ok": True}
