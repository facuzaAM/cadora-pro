"""Add editor support columns to projects

Revision ID: 010
Revises: 009
Create Date: 2026-08-06
"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("detection_result", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("edited_elements", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "edited_elements")
    op.drop_column("projects", "detection_result")
