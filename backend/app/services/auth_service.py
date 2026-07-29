import asyncio
import logging
import secrets as _secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest, TokenResponse, UserResponse
from app.utils.jwt import create_access_token, create_refresh_token, decode_refresh_token
from app.utils.security import hash_password, verify_password

logger = logging.getLogger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)
        self.refresh_repo = RefreshTokenRepository(db)
        self.reset_repo = PasswordResetRepository(db)

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

    async def _send_code(
        self, user: User, subject: str, email_fn, log_action: str
    ) -> bool:
        code = str(_secrets.randbelow(900000) + 100000)
        expires_at = datetime.now(UTC) + timedelta(minutes=15)
        user.email_verification_code = code
        user.email_verification_expires_at = expires_at
        await self.repo._save(user)
        sent = await asyncio.to_thread(email_fn, user.email, code, user.name)
        if not sent:
            logger.error(
                "Failed to send %s email to %s (user %s)",
                log_action, user.email, user.id,
            )
        return sent

    async def send_verification_email(self, user: User) -> bool:
        from app.services.email_service import send_verification_code

        if user.email_verified:
            return True
        return await self._send_code(
            user,
            "Verificá tu email",
            send_verification_code,
            "verification",
        )

    async def verify_email(self, user: User, code: str) -> None:
        if user.email_verified:
            raise ValueError("El email ya está verificado")
        if not user.email_verification_code or not user.email_verification_expires_at:
            raise ValueError("No hay código de verificación pendiente")
        if user.email_verification_expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
            raise ValueError("El código expiró. Solicitá uno nuevo.")
        if user.email_verification_code != code:
            raise ValueError("Código incorrecto")
        user.email_verified = True
        user.email_verification_code = None
        user.email_verification_expires_at = None
        await self.repo._save(user)

    async def forgot_password(self, email: str) -> bool:
        """Generate a 6-digit reset code and email it. Always returns True."""
        from app.services.email_service import send_reset_code

        user = await self.repo.get_by_email(email)
        if not user:
            return True

        await self.reset_repo.invalidate_all_for_user(user.id)

        code = str(_secrets.randbelow(900000) + 100000)
        expires_at = datetime.now(UTC) + timedelta(minutes=15)
        await self.reset_repo.create(user.id, code, expires_at)

        sent = await asyncio.to_thread(send_reset_code, user.email, code, user.name)
        if not sent:
            logger.error(
                "Failed to send password reset email to %s (user %s)",
                user.email, user.id,
            )
        return True

    async def reset_password(self, code: str, new_password: str) -> None:
        """Reset a user's password using a valid 6-digit code."""
        token = await self.reset_repo.get_valid_code(code)
        if not token:
            raise ValueError("Código inválido o expirado")

        user = await self.repo.get_by_id(token.user_id)
        if not user:
            raise ValueError("Usuario no encontrado")

        user.hashed_password = hash_password(new_password)
        await self.repo._save(user)
        await self.reset_repo.mark_used(token.id)
        await self.refresh_repo.revoke_all_for_user(user.id)

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
