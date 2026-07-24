from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest, TokenResponse, UserResponse
from app.utils.jwt import create_access_token, create_refresh_token, decode_refresh_token
from app.utils.security import hash_password, verify_password


class AuthService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)
        self.refresh_repo = RefreshTokenRepository(db)

    async def register(self, request: RegisterRequest) -> TokenResponse:
        existing = await self.repo.get_by_email(request.email)
        if existing:
            raise ValueError("El email ya está registrado")

        hashed = hash_password(request.password)
        user = await self.repo.create(
            email=request.email, name=request.name, hashed_password=hashed
        )
        return await self._build_token(user)

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Email o contraseña incorrectos")

        return await self._build_token(user)

    async def refresh(self, refresh_token_str: str) -> TokenResponse:
        payload = decode_refresh_token(refresh_token_str)
        if not payload:
            raise ValueError("Refresh token inválido o expirado")

        rt = await self.refresh_repo.get_by_token(refresh_token_str)
        if not rt or rt.revoked:
            raise ValueError("Refresh token inválido")
        if rt.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            raise ValueError("Refresh token expirado")

        user = await self.repo.get_by_id(rt.user_id)
        if not user:
            raise ValueError("Usuario no encontrado")

        await self.refresh_repo.revoke(refresh_token_str)

        return await self._build_token(user)

    async def logout(self, refresh_token_str: str) -> None:
        await self.refresh_repo.revoke(refresh_token_str)

    async def logout_all(self, user_id: UUID) -> None:
        await self.refresh_repo.revoke_all_for_user(user_id)

    async def change_password(
        self, user_id: UUID, current_password: str, new_password: str
    ) -> None:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        if not verify_password(current_password, user.hashed_password):
            raise ValueError("La contraseña actual es incorrecta")
        user.hashed_password = hash_password(new_password)
        await self.repo._save(user)

    async def get_user(self, user_id: UUID) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        return user

    async def _build_token(self, user: User) -> TokenResponse:
        payload = {"sub": str(user.id), "token_version": user.token_version}
        access_token = create_access_token(payload)
        refresh_token = create_refresh_token(payload)

        expires_at = datetime.now(UTC) + timedelta(
            days=settings.JWT_REFRESH_EXPIRATION_DAYS
        )
        await self.refresh_repo.create(
            user_id=user.id,
            token=refresh_token,
            expires_at=expires_at,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.model_validate(user),
        )
