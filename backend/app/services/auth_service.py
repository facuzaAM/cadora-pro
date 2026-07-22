from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest, TokenResponse, UserResponse
from app.utils.jwt import create_access_token
from app.utils.security import hash_password, verify_password


class AuthService:
    def __init__(self, db: AsyncSession):
        self.repo = UserRepository(db)

    async def register(self, request: RegisterRequest) -> TokenResponse:
        existing = await self.repo.get_by_email(request.email)
        if existing:
            raise ValueError("El email ya está registrado")

        hashed = hash_password(request.password)
        user = await self.repo.create(
            email=request.email, name=request.name, hashed_password=hashed
        )
        return self._build_token(user)

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Email o contraseña incorrectos")

        return self._build_token(user)

    async def get_user(self, user_id: UUID) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise ValueError("Usuario no encontrado")
        return user

    def _build_token(self, user: User) -> TokenResponse:
        token = create_access_token({"sub": str(user.id)})
        return TokenResponse(
            access_token=token,
            user=UserResponse.model_validate(user),
        )
