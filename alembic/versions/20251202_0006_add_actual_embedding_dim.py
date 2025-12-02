"""Add actual_embedding_dim to users table

Revision ID: 20251202_0006
Revises: 20251205_0005
Create Date: 2025-12-02 00:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251202_0006'
down_revision = '20251205_0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add actual_embedding_dim column to users table
    op.add_column('users', sa.Column('actual_embedding_dim', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Remove actual_embedding_dim column from users table
    op.drop_column('users', 'actual_embedding_dim')
