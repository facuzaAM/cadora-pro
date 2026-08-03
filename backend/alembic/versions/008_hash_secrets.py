"""Hash secrets at rest (refresh tokens, reset codes, verification codes)

Revision ID: 008
Revises: 007
Create Date: 2026-07-31
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Clear legacy plaintext secrets that no longer fit the hashed column
    # sizes (a 212-char raw JWT would make the VARCHAR(64) ALTER fail).
    op.execute(sa.text("DELETE FROM refresh_tokens WHERE LENGTH(token) > 64"))
    op.execute(sa.text("DELETE FROM password_reset_tokens WHERE LENGTH(code) > 64"))
    op.execute(sa.text("DELETE FROM users WHERE LENGTH(email_verification_code) > 64"))

    op.alter_column("refresh_tokens", "token", type_=sa.String(64), existing_type=sa.String(512))
    op.alter_column("password_reset_tokens", "code", type_=sa.String(64), existing_type=sa.String(6))
    op.alter_column("users", "email_verification_code", type_=sa.String(64), existing_type=sa.String(6))


def downgrade() -> None:
    op.alter_column("users", "email_verification_code", type_=sa.String(6), existing_type=sa.String(64))
    op.alter_column("password_reset_tokens", "code", type_=sa.String(6), existing_type=sa.String(64))
    op.alter_column("refresh_tokens", "token", type_=sa.String(512), existing_type=sa.String(64))
