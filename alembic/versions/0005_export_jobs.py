"""add export_jobs table

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-29 18:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "export_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("format", sa.String(20), nullable=False, server_default="zip"),
        sa.Column("filename", sa.String(512), server_default=""),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("file_path", sa.String(1024), server_default=""),
        sa.Column("error_message", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_export_jobs_workspace_id", "export_jobs", ["workspace_id"])
    op.create_index("ix_export_jobs_status", "export_jobs", ["workspace_id", "status"])
    op.create_index("ix_export_jobs_created_at", "export_jobs", ["workspace_id", "created_at"])


def downgrade() -> None:
    op.drop_table("export_jobs")
