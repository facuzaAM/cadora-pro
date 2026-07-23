import uuid
from datetime import UTC, datetime

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Stripe / billing
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscription_plan: Mapped[str] = mapped_column(
        String(50), nullable=False, default="free"
    )
    subscription_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="inactive"
    )
    subscription_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Usage tracking
    conversions_used: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    conversions_limit: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=3
    )
    conversions_reset_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    storage_used: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    storage_limit: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=50 * 1024 * 1024
    )
    priority_processing: Mapped[bool] = mapped_column(
        nullable=False, default=False
    )
    token_version: Mapped[int] = mapped_column(nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
