import secrets
from typing import Literal
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    LoginRequest,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.utils.dependencies import get_current_user
from app.utils.rate_limit import limiter

router = APIRouter()

ACCESS_COOKIE = "cadora_access"
REFRESH_COOKIE = "cadora_refresh"
COOKIE_SECURE = True
COOKIE_SAMESITE: Literal["none"] = "none"


def _auth_response(tokens: TokenResponse, user: User) -> JSONResponse:
    """Create a JSON response with refresh token as HttpOnly cookie."""
    resp = JSONResponse(content={
        "access_token": tokens.access_token,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "avatar_url": user.avatar_url,
            "subscription_plan": user.subscription_plan,
            "subscription_status": user.subscription_status,
            "conversions_used": user.conversions_used,
            "conversions_limit": user.conversions_limit,
            "storage_used": user.storage_used,
            "storage_limit": user.storage_limit,
            "priority_processing": user.priority_processing,
            "created_at": user.created_at.isoformat() if user.created_at else "",
        },
    })
    resp.set_cookie(
        key=REFRESH_COOKIE,
        value=tokens.refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=7 * 24 * 3600,
        path="/",
    )
    return resp

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/google")
async def google_login():
    """Redirect to Google OAuth consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Google OAuth no configurado",
        )
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Google OAuth callback, create/find user, return tokens."""
    code = request.query_params.get("code")
    error = request.query_params.get("error")
    if error:
        return RedirectResponse(f"/login?error={error}")
    if not code:
        return RedirectResponse("/login?error=no_code")

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            return RedirectResponse("/login?error=token_exchange_failed")
        token_data = token_resp.json()

        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        if userinfo_resp.status_code != 200:
            return RedirectResponse("/login?error=userinfo_failed")
        userinfo = userinfo_resp.json()

    email = userinfo.get("email")
    name = userinfo.get("name", email.split("@")[0] if email else "user")
    avatar_url = userinfo.get("picture")

    if not email:
        return RedirectResponse("/login?error=no_email")

    repo = UserRepository(db)
    user = await repo.get_by_email(email)

    if not user:
        from app.utils.security import hash_password
        random_password = secrets.token_hex(32)
        hashed = hash_password(random_password)
        user = await repo.create(
            email=email, name=name, hashed_password=hashed,
        )
        user.avatar_url = avatar_url
        await repo._save(user)

    service = AuthService(db)
    tokens = await service._build_token(user)

    frontend_url = str(request.base_url).rstrip("/")
    resp = RedirectResponse(f"{frontend_url}/login")
    resp.set_cookie(
        key=REFRESH_COOKIE,
        value=tokens.refresh_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 3600,
        path="/",
    )
    resp.set_cookie(
        key=ACCESS_COOKIE,
        value=tokens.access_token,
        httponly=False,
        secure=True,
        samesite="none",
        max_age=15 * 60,
        path="/",
    )
    return resp


@router.post("/register")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    try:
        result = await service.register(body)
    except ValueError as e:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail=str(e)
        )
    user = await service.repo.get_by_email(body.email)
    if not user:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Error creando usuario",
        )
    return _auth_response(result, user)


@router.post("/login")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    try:
        result = await service.login(body.email, body.password)
    except ValueError as e:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST, detail=str(e)
        )
    user = await service.repo.get_by_email(body.email)
    if not user:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Error obteniendo usuario",
        )
    return _auth_response(result, user)


@router.post("/refresh")
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def refresh(
    request: Request,
    body: RefreshRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    token = None
    if body and body.refresh_token:
        token = body.refresh_token
    if not token:
        token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided",
        )
    try:
        result = await service.refresh(token)
    except ValueError as e:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail=str(e)
        )
    user = await service.repo.get_by_id(result.user.id)
    if not user:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
        )
    return _auth_response(result, user)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    body: RefreshRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    token = None
    if body and body.refresh_token:
        token = body.refresh_token
    if not token:
        token = request.cookies.get(REFRESH_COOKIE)
    if token:
        await service.logout(token)
    resp = JSONResponse(status_code=204, content=None)
    resp.delete_cookie(REFRESH_COOKIE, path="/")
    resp.delete_cookie(ACCESS_COOKIE, path="/")
    return resp


@router.get("/me", response_model=UserResponse)
async def me(user=Depends(get_current_user)):
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    if body.name is not None:
        user.name = body.name.strip()
    if body.avatar_url is not None:
        user.avatar_url = body.avatar_url
    await repo._save(user)
    return UserResponse.model_validate(user)
