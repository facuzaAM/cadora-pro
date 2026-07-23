"""Rename stripe_customer_id to paddle_customer_id, add paddle_subscription_id

Revision ID: 005
Revises: 004
Create Date: 2025-03-01
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("users", "stripe_customer_id", new_column_name="paddle_customer_id")
    op.add_column("users", sa.Column("paddle_subscription_id", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "paddle_subscription_id")
    op.alter_column("users", "paddle_customer_id", new_column_name="stripe_customer_id")
