import secrets
import uuid
from typing import Literal
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    DeleteAccountRequest,
    ForgotPasswordRequest,
    LoginRequest,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.account_service import AccountService
from app.services.auth_service import AuthService
from app.utils.dependencies import ACCESS_TOKEN_COOKIE, get_current_user
from app.utils.rate_limit import rate_limit

router = APIRouter()

ACCESS_COOKIE = ACCESS_TOKEN_COOKIE
REFRESH_COOKIE = "cadora_refresh"


def _cookie_secure() -> bool:
    return settings.ENVIRONMENT == "production"


def _cookie_samesite() -> Literal["none", "lax"]:
    return "none" if settings.ENVIRONMENT == "production" else "lax"


def _cookie_domain() -> str | None:
    """Parent domain so auth cookies are shared across app./api. subdomains.

    The frontend calls the API via the same-origin path (``/api/v1`` on
    app.cadora.pro), but the Google OAuth callback lives on api.cadora.pro.
    A host-only cookie set on one subdomain is invisible on the other, so the
    OAuth ``state`` check (and the session cookies set by the callback) fail.
    Scoping them to the parent domain fixes the hand-off.
    """
    if settings.ENVIRONMENT != "production":
        return None
    host = urlparse(settings.FRONTEND_URL or "cadora.pro").hostname or "cadora.pro"
    for prefix in ("app.", "www."):
        if host.startswith(prefix):
            host = host[len(prefix) :]
    return f".{host}"


def _frontend_redirect(path: str) -> RedirectResponse:
    base = settings.FRONTEND_URL or ""
    return RedirectResponse(f"{base}{path}")


def _auth_response(tokens: TokenResponse, user: User) -> JSONResponse:
    """Create a JSON response with refresh token as HttpOnly cookie."""
    resp = JSONResponse(
        content={
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
                "is_admin": user.is_admin,
                "email_verified": user.email_verified,
                "created_at": user.created_at.isoformat() if user.created_at else "",
            },
        }
    )
    resp.set_cookie(
        key=REFRESH_COOKIE,
        value=tokens.refresh_token,
        httponly=True,
        secure=_cookie_secure(),
        samesite=_cookie_samesite(),
        domain=_cookie_domain(),
        max_age=7 * 24 * 3600,
        path="/",
    )
    resp.set_cookie(
        key=ACCESS_COOKIE,
        value=tokens.access_token,
        httponly=True,
        secure=_cookie_secure(),
        samesite=_cookie_samesite(),
        domain=_cookie_domain(),
        max_age=settings.JWT_ACCESS_EXPIRATION_MINUTES * 60,
        path="/",
    )
    return resp


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def _derive_google_redirect_uri(request: Request) -> str:
    """Build the OAuth callback URL from the API host actually serving the request.

    Using FRONTEND_URL here is wrong: the callback lives on the API, not the
    frontend. When running behind nginx the ``Host``/``X-Forwarded-Proto``
    headers resolve to the API domain (e.g. api.cadora.pro), which is the
    address Google must redirect back to.
    """
    scheme = request.headers.get("X-Forwarded-Proto", "https")
    host = request.headers.get("Host", "api.cadora.pro")
    return f"{scheme}://{host}/api/v1/auth/google/callback"


@router.get("/google")
async def google_login(request: Request):
    """Redirect to Google OAuth consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Google OAuth no configurado",
        )
    redirect_uri = settings.GOOGLE_REDIRECT_URI or _derive_google_redirect_uri(request)
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
    }
    resp = RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")
    resp.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=_cookie_secure(),
        samesite=_cookie_samesite(),
        domain=_cookie_domain(),
        max_age=600,
        path="/",
    )
    return resp


@router.get("/google/callback")
async def google_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Google OAuth callback, create/find user, return tokens."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    stored_state = request.cookies.get("oauth_state")
    if not state or not stored_state or not secrets.compare_digest(state, stored_state):
        return _frontend_redirect("/login?error=invalid_state")

    resp = _frontend_redirect("/login")
    resp.delete_cookie("oauth_state", path="/", domain=_cookie_domain())

    if error:
        return _frontend_redirect(f"/login?error={error}")
    if not code:
        return _frontend_redirect("/login?error=no_code")

    redirect_uri = settings.GOOGLE_REDIRECT_URI or _derive_google_redirect_uri(request)

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            return _frontend_redirect("/login?error=token_exchange_failed")
        token_data = token_resp.json()

        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        if userinfo_resp.status_code != 200:
            return _frontend_redirect("/login?error=userinfo_failed")
        userinfo = userinfo_resp.json()

    email = (userinfo.get("email") or "").strip().lower()
    name = userinfo.get("name", email.split("@")[0] if email else "user")
    avatar_url = userinfo.get("picture")

    if not email:
        return _frontend_redirect("/login?error=no_email")

    repo = UserRepository(db)
    user = await repo.get_by_email(email)

    if not user:
        from app.utils.security import hash_password

        random_password = secrets.token_hex(32)
        hashed = hash_password(random_password)
        user = await repo.create(
            email=email,
            name=name,
            hashed_password=hashed,
        )

    user.avatar_url = avatar_url or user.avatar_url
    user.email_verified = True
    await repo._save(user)

    service = AuthService(db)
    tokens = await service._build_token(user)

    resp = _frontend_redirect("/auth/callback")
    resp.set_cookie(
        key=REFRESH_COOKIE,
        value=tokens.refresh_token,
        httponly=True,
        secure=_cookie_secure(),
        samesite=_cookie_samesite(),
        domain=_cookie_domain(),
        max_age=7 * 24 * 3600,
        path="/",
    )
    resp.set_cookie(
        key=ACCESS_COOKIE,
        value=tokens.access_token,
        httponly=True,
        secure=_cookie_secure(),
        samesite=_cookie_samesite(),
        domain=_cookie_domain(),
        max_age=settings.JWT_ACCESS_EXPIRATION_MINUTES * 60,
        path="/",
    )
    return resp


@router.post("/register")
@rate_limit(settings.RATE_LIMIT_AUTH)
async def register(
    request: Request,
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    try:
        result = await service.register(body)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    user = await service.repo.get_by_email(body.email)
    if not user:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Error creando usuario",
        )
    if settings.ENVIRONMENT != "production":
        user.email_verified = True
        await service.repo._save(user)
    else:
        if not settings.SMTP_HOST:
            raise HTTPException(
                status_code=HTTP_503_SERVICE_UNAVAILABLE,
                detail="El servicio de email no está configurado. "
                "No se pudo enviar el código de verificación.",
            )
        await service.send_verification_email(user)
    return _auth_response(result, user)


@router.post("/login")
@rate_limit(settings.RATE_LIMIT_AUTH)
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    try:
        result = await service.login(body.email, body.password)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    user = await service.repo.get_by_email(body.email)
    if not user:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="Error obteniendo usuario",
        )
    return _auth_response(result, user)


@router.post("/refresh")
@rate_limit(settings.RATE_LIMIT_AUTH)
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
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail=str(e))
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
    resp = Response(status_code=204)
    resp.delete_cookie(REFRESH_COOKIE, path="/", domain=_cookie_domain())
    resp.delete_cookie(ACCESS_COOKIE, path="/", domain=_cookie_domain())
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


@router.post("/change-password", status_code=204)
@rate_limit("5/minute")
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    try:
        await service.change_password(user.id, body.current_password, body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Formato no soportado. Usa JPG, PNG o WebP.")

    max_bytes = 5 * 1024 * 1024
    data = b""
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        data += chunk
        if len(data) > max_bytes:
            raise HTTPException(status_code=413, detail="La imagen no puede superar 5 MB.")

    if not _is_valid_image(data):
        raise HTTPException(status_code=400, detail="Archivo de imagen inválido")

    ext = file.content_type.rsplit("/", 1)[-1]
    if ext == "jpeg":
        ext = "jpg"
    path = f"avatars/{user.id}/{uuid.uuid4().hex}.{ext}"

    from app.services.storage_service import StorageService

    storage = StorageService()
    await storage.upload(settings.STORAGE_BUCKET, path, data, file.content_type)
    url = await storage.get_download_url(settings.STORAGE_BUCKET, path)

    user.avatar_url = url
    repo = UserRepository(db)
    await repo._save(user)

    return {"avatar_url": url}


def _is_valid_image(data: bytes) -> bool:
    """Validate image magic bytes to reject spoofed content types."""
    return bool(
        data
        and (
            data.startswith(b"\x89PNG\r\n\x1a\n")
            or data.startswith(b"\xff\xd8\xff")
            or (len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP")
        )
    )


@router.post("/logout-all", status_code=204)
async def logout_all(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    await service.logout_all(user.id)
    resp = Response(status_code=204)
    resp.delete_cookie(REFRESH_COOKIE, path="/", domain=_cookie_domain())
    resp.delete_cookie(ACCESS_COOKIE, path="/", domain=_cookie_domain())
    return resp


@router.post("/forgot-password", status_code=204)
@rate_limit("3/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    await service.forgot_password(body.email)


@router.post("/reset-password")
@rate_limit("5/minute")
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    try:
        await service.reset_password(body.code, body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    return {"message": "Contraseña actualizada correctamente"}


@router.post("/send-verification")
@rate_limit("3/minute")
async def send_verification(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    if user.email_verified:
        return {"message": "El email ya está verificado"}
    sent = await service.send_verification_email(user)
    if not sent:
        return JSONResponse(
            status_code=500,
            content={"detail": "No pudimos enviar el código. Intentá de nuevo más tarde."},
        )
    return {"message": "Código enviado a tu email"}


@router.post("/verify-email")
@rate_limit("5/minute")
async def verify_email(
    request: Request,
    body: VerifyEmailRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AuthService(db)
    try:
        await service.verify_email(user, body.code)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    return {"message": "Email verificado correctamente"}


@router.get("/me/export")
@rate_limit("5/minute")
async def export_user_data(
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AccountService(db)
    try:
        return await service.export_user_data(user.id)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/me", status_code=204)
@rate_limit("5/minute")
async def delete_account(
    request: Request,
    body: DeleteAccountRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = AccountService(db)
    try:
        await service.delete_account(user.id, body.password)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    resp = Response(status_code=204)
    resp.delete_cookie(REFRESH_COOKIE, path="/", domain=_cookie_domain())
    resp.delete_cookie(ACCESS_COOKIE, path="/", domain=_cookie_domain())
    return resp
