"""Add Stripe billing fields to users

Revision ID: 002
Revises: 001
Create Date: 2024-06-01
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("stripe_customer_id", sa.String(255), nullable=True))
    op.add_column("users", sa.Column(
        "subscription_plan", sa.String(50),
        nullable=False, server_default="free",
    ))
    op.add_column("users", sa.Column(
        "subscription_status", sa.String(50),
        nullable=False, server_default="inactive",
    ))
    op.add_column("users", sa.Column(
        "subscription_end", sa.DateTime(timezone=True), nullable=True,
    ))
    op.add_column("users", sa.Column(
        "conversions_used", sa.BigInteger(),
        nullable=False, server_default="0",
    ))
    op.add_column("users", sa.Column(
        "conversions_limit", sa.BigInteger(),
        nullable=False, server_default="5",
    ))
    op.add_column("users", sa.Column(
        "storage_used", sa.BigInteger(),
        nullable=False, server_default="0",
    ))
    op.add_column("users", sa.Column(
        "storage_limit", sa.BigInteger(),
        nullable=False, server_default="52428800",
    ))
    op.add_column("users", sa.Column(
        "priority_processing", sa.Boolean(),
        nullable=False, server_default="false",
    ))


def downgrade() -> None:
    op.drop_column("users", "stripe_customer_id")
    op.drop_column("users", "subscription_plan")
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "subscription_end")
    op.drop_column("users", "conversions_used")
    op.drop_column("users", "conversions_limit")
    op.drop_column("users", "storage_used")
    op.drop_column("users", "storage_limit")
    op.drop_column("users", "priority_processing")
