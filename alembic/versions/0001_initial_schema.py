"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-29 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("bucket_path", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("email", sa.String(320), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), server_default="viewer"),
        sa.Column("attributes", postgresql.JSON(), server_default="{}"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "nodes",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("concept_path", sa.String(1024), nullable=False),
        sa.Column("title", sa.String(512), server_default=""),
        sa.Column("node_type", sa.String(100), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String()), server_default="{}"),
        sa.Column("status", sa.Enum("draft", "published", "archived", name="nodestatus"),
                  server_default="draft"),
        sa.Column("source_hash", sa.String(64), server_default=""),
        sa.Column("file_size", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "edges",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("source_id", sa.String(), sa.ForeignKey("nodes.id"), nullable=False),
        sa.Column("target_id", sa.String(), sa.ForeignKey("nodes.id"), nullable=False),
        sa.Column("edge_type",
                  sa.Enum("references", "depends_on", "parent_of", "related_to", name="edgetype"),
                  server_default="references"),
        sa.Column("metadata", postgresql.JSON(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action",
                  sa.Enum("ingest", "query", "approve", "reject", "export", "delete",
                          name="auditaction"),
                  nullable=False),
        sa.Column("resource_type", sa.String(50), server_default=""),
        sa.Column("resource_id", sa.String(100), server_default=""),
        sa.Column("details", postgresql.JSON(), server_default="{}"),
        sa.Column("ip_address", sa.String(45), server_default=""),
        sa.Column("cost_estimate", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("edges")
    op.drop_table("nodes")
    op.drop_table("users")
    op.drop_table("workspaces")
    sa.Enum(name="auditaction").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="edgetype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="nodestatus").drop(op.get_bind(), checkfirst=True)
