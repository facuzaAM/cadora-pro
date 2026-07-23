"""Add conversions_reset_at and update free plan limit to 3

Revision ID: 003
Revises: 002
Create Date: 2025-01-01
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("conversions_reset_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE users SET conversions_limit = 3 WHERE subscription_plan = 'free'"
    )


def downgrade() -> None:
    op.drop_column("users", "conversions_reset_at")
    op.execute(
        "UPDATE users SET conversions_limit = 5 WHERE subscription_plan = 'free'"
    )
