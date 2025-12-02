"""add avatar path to personas

Revision ID: 20251205_0005
Revises: 20251202_0004
Create Date: 2025-12-05 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251205_0005'
down_revision = '20251202_0004'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('personas') as batch_op:
        batch_op.add_column(sa.Column('avatar_path', sa.String(length=512), nullable=True))


def downgrade():
    with op.batch_alter_table('personas') as batch_op:
        batch_op.drop_column('avatar_path')
