"""add connector_configs table

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-29 15:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "connector_configs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("connector_type", sa.String(50), nullable=False),
        sa.Column("label", sa.String(255), server_default=""),
        sa.Column("config", postgresql.JSON() if op.get_context().dialect.name == "postgresql"
                  else sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("last_status", sa.String(100), server_default=""),
        sa.Column("last_polled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "connector_type", name="uq_connector_workspace_type"),
    )
    op.create_index("ix_connector_configs_workspace_id", "connector_configs", ["workspace_id"])


def downgrade() -> None:
    op.drop_table("connector_configs")
