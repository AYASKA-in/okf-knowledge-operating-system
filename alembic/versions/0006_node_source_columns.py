"""add source_connector and source_original_id to nodes

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-29 19:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("nodes", sa.Column("source_connector", sa.String(50), nullable=True))
    op.add_column("nodes", sa.Column("source_original_id", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("nodes", "source_original_id")
    op.drop_column("nodes", "source_connector")
