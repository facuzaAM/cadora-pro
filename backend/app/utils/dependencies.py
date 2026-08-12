from uuid import UUID

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_401_UNAUTHORIZED

from app.database import get_db
from app.repositories.user_repository import UserRepository
from app.utils.jwt import decode_access_token

ACCESS_TOKEN_COOKIE = "cadora_access"

security = HTTPBearer(auto_error=False)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(security),
    db: AsyncSession = Depends(get_db),
):
    # Auth only via Authorization header or the HttpOnly access cookie. The
    # access token must never travel in a query string: it leaks into logs,
    # the Referer header and browser history. The same-origin preview <img>
    # already sends the HttpOnly cookie, so no endpoint needs ?token=...
    token = credentials.credentials if credentials else None
    if not token:
        token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if not token:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
        )

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    token_version = payload.get("token_version", 0)
    repo = UserRepository(db)
    try:
        user = await repo.get_by_id(UUID(str(user_id)))
    except ValueError:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    if not user:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )
    if user.token_version != token_version:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Token revocado",
        )
    return user
