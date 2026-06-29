"""add ingest_jobs table

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-29 15:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingest_jobs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("filename", sa.String(512), server_default=""),
        sa.Column("source_type", sa.String(50), server_default=""),
        sa.Column("status",
                  sa.Enum("pending", "running", "done", "failed", name="ingestjobstatus"),
                  nullable=False, server_default="pending"),
        sa.Column("progress_pct", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=False, server_default=""),
        sa.Column("result_summary", postgresql.JSON() if op.get_context().dialect.name == "postgresql"
                  else sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ingest_jobs_workspace_id", "ingest_jobs", ["workspace_id"])
    op.create_index("ix_ingest_jobs_status", "ingest_jobs", ["workspace_id", "status"])
    op.create_index("ix_ingest_jobs_created_at", "ingest_jobs", ["workspace_id", "created_at"])


def downgrade() -> None:
    op.drop_table("ingest_jobs")
    op.execute("DROP TYPE IF EXISTS ingestjobstatus")
