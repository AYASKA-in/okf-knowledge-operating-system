"""add chunk_index, parent_hash, token_count to nodes

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-29 20:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("nodes", sa.Column("chunk_index", sa.Integer(), nullable=True))
    op.add_column("nodes", sa.Column("parent_hash", sa.String(64), nullable=True))
    op.add_column("nodes", sa.Column("token_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("nodes", "token_count")
    op.drop_column("nodes", "parent_hash")
    op.drop_column("nodes", "chunk_index")
