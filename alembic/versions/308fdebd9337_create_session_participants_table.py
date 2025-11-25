"""create_session_participants_table

Revision ID: 308fdebd9337
Revises: 20241124_0002
Create Date: 2025-11-24 21:15:36.481935

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '308fdebd9337'
down_revision = '20241124_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "session_participants",
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("persona_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id", "persona_id"),
    )


def downgrade() -> None:
    op.drop_table("session_participants")
