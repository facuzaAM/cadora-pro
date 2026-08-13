"""Add activity_events table for audit trail and conversion history."""

from __future__ import annotations

from typing import ClassVar

import sqlalchemy as sa
from alembic import op

revision: str = "013_activity_events"
down_revision: str = "012_project_conversion_charged"
branch_labels: ClassVar[str | None] = None
depends_on: ClassVar[str | None] = None


def upgrade() -> None:
    op.create_table(
        "activity_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activity_events_user", "activity_events",
                    ["user_id", sa.text("created_at DESC")])
    op.create_index("ix_activity_events_project", "activity_events",
                    ["project_id", sa.text("created_at DESC")])


def downgrade() -> None:
    op.drop_index("ix_activity_events_project", table_name="activity_events")
    op.drop_index("ix_activity_events_user", table_name="activity_events")
    op.drop_table("activity_events")
