"""add session meta fields

Revision ID: 20251201_0003
Revises: 634ef3ac2bc0
Create Date: 2025-12-01 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251201_0003'
down_revision = '634ef3ac2bc0'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('sessions') as batch_op:
        batch_op.add_column(sa.Column('title', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('user_display_name', sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column('user_handle', sa.String(length=128), nullable=True))


def downgrade():
    with op.batch_alter_table('sessions') as batch_op:
        batch_op.drop_column('user_handle')
        batch_op.drop_column('user_display_name')
        batch_op.drop_column('title')
