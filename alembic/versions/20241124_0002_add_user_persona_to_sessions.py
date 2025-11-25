"""Add user persona to sessions."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20241124_0002"
down_revision = "20240722_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("user_persona", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "user_persona")
