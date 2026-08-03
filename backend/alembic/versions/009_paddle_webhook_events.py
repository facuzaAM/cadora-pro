"""Persist Paddle webhook events for idempotent processing

Revision ID: 009
Revises: 008
Create Date: 2026-08-03
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "paddle_webhook_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_paddle_webhook_events_event_id", "paddle_webhook_events", ["event_id"], unique=True
    )
    op.create_index(
        "ix_paddle_webhook_events_processed_at", "paddle_webhook_events", ["processed_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_paddle_webhook_events_processed_at", table_name="paddle_webhook_events")
    op.drop_index("ix_paddle_webhook_events_event_id", table_name="paddle_webhook_events")
    op.drop_table("paddle_webhook_events")
