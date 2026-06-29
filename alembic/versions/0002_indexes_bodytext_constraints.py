"""add indexes, body_text, constraints, user updated_at

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-29 14:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- nodes: add body_text column ---
    op.add_column("nodes", sa.Column("body_text", sa.Text(), server_default=""))

    # --- nodes: unique constraint on (workspace_id, concept_path) ---
    op.create_unique_constraint("uq_node_workspace_path", "nodes", ["workspace_id", "concept_path"])

    # --- nodes: indexes ---
    op.create_index("ix_nodes_workspace_id", "nodes", ["workspace_id"])
    op.create_index("ix_nodes_node_type", "nodes", ["workspace_id", "node_type"])
    op.create_index("ix_nodes_status", "nodes", ["workspace_id", "status"])
    op.create_index("ix_nodes_updated_at", "nodes", ["workspace_id", "updated_at"])

    # --- workspaces: index ---
    op.create_index("ix_workspaces_name", "workspaces", ["name"])

    # --- users: indexes + updated_at ---
    op.create_index("ix_users_workspace_id", "users", ["workspace_id"])

    op.add_column("users", sa.Column("updated_at", sa.DateTime(timezone=True),
                                     server_default=sa.func.now()))

    # --- edges: indexes + unique constraint ---
    op.create_index("ix_edges_workspace_id", "edges", ["workspace_id"])
    op.create_index("ix_edges_source", "edges", ["source_id"])
    op.create_index("ix_edges_target", "edges", ["target_id"])
    op.create_unique_constraint("uq_edge_pair", "edges", ["source_id", "target_id", "edge_type"])

    # --- audit_logs: indexes ---
    op.create_index("ix_audit_workspace_id", "audit_logs", ["workspace_id"])
    op.create_index("ix_audit_created_at", "audit_logs", ["workspace_id", "created_at"])
    op.create_index("ix_audit_action", "audit_logs", ["workspace_id", "action"])

    # --- drop old FK constraints and recreate with ON DELETE CASCADE ---
    # users: workspace_id
    op.drop_constraint("users_workspace_id_fkey", "users", type_="foreignkey")
    op.create_foreign_key("users_workspace_id_fkey", "users", "workspaces",
                          ["workspace_id"], ["id"], ondelete="CASCADE")

    # nodes: workspace_id
    op.drop_constraint("nodes_workspace_id_fkey", "nodes", type_="foreignkey")
    op.create_foreign_key("nodes_workspace_id_fkey", "nodes", "workspaces",
                          ["workspace_id"], ["id"], ondelete="CASCADE")

    # edges: workspace_id, source_id, target_id
    op.drop_constraint("edges_workspace_id_fkey", "edges", type_="foreignkey")
    op.create_foreign_key("edges_workspace_id_fkey", "edges", "workspaces",
                          ["workspace_id"], ["id"], ondelete="CASCADE")
    op.drop_constraint("edges_source_id_fkey", "edges", type_="foreignkey")
    op.create_foreign_key("edges_source_id_fkey", "edges", "nodes",
                          ["source_id"], ["id"], ondelete="CASCADE")
    op.drop_constraint("edges_target_id_fkey", "edges", type_="foreignkey")
    op.create_foreign_key("edges_target_id_fkey", "edges", "nodes",
                          ["target_id"], ["id"], ondelete="CASCADE")

    # audit_logs: workspace_id
    op.drop_constraint("audit_logs_workspace_id_fkey", "audit_logs", type_="foreignkey")
    op.create_foreign_key("audit_logs_workspace_id_fkey", "audit_logs", "workspaces",
                          ["workspace_id"], ["id"], ondelete="CASCADE")
    op.drop_constraint("audit_logs_user_id_fkey", "audit_logs", type_="foreignkey")
    op.create_foreign_key("audit_logs_user_id_fkey", "audit_logs", "users",
                          ["user_id"], ["id"], ondelete="SET NULL")

    # --- add 'chat' to auditaction enum ---
    op.execute("ALTER TYPE auditaction ADD VALUE 'chat'")


def downgrade() -> None:
    # removal order: indexes before columns before constraints
    op.drop_index("ix_audit_action", table_name="audit_logs")
    op.drop_index("ix_audit_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_workspace_id", table_name="audit_logs")
    op.drop_index("ix_edges_target", table_name="edges")
    op.drop_index("ix_edges_source", table_name="edges")
    op.drop_index("ix_edges_workspace_id", table_name="edges")
    op.drop_index("ix_users_workspace_id", table_name="users")
    op.drop_index("ix_workspaces_name", table_name="workspaces")
    op.drop_index("ix_nodes_updated_at", table_name="nodes")
    op.drop_index("ix_nodes_status", table_name="nodes")
    op.drop_index("ix_nodes_node_type", table_name="nodes")
    op.drop_index("ix_nodes_workspace_id", table_name="nodes")

    op.drop_constraint("uq_node_workspace_path", "nodes", type_="unique")
    op.drop_constraint("uq_edge_pair", "edges", type_="unique")

    op.drop_column("users", "updated_at")
    op.drop_column("nodes", "body_text")

    # Restore original FK constraints (without ON DELETE)
    op.drop_constraint("audit_logs_user_id_fkey", "audit_logs", type_="foreignkey")
    op.create_foreign_key("audit_logs_user_id_fkey", "audit_logs", "users",
                          ["user_id"], ["id"])
    op.drop_constraint("audit_logs_workspace_id_fkey", "audit_logs", type_="foreignkey")
    op.create_foreign_key("audit_logs_workspace_id_fkey", "audit_logs", "workspaces",
                          ["workspace_id"], ["id"])
    op.drop_constraint("edges_target_id_fkey", "edges", type_="foreignkey")
    op.create_foreign_key("edges_target_id_fkey", "edges", "nodes",
                          ["target_id"], ["id"])
    op.drop_constraint("edges_source_id_fkey", "edges", type_="foreignkey")
    op.create_foreign_key("edges_source_id_fkey", "edges", "nodes",
                          ["source_id"], ["id"])
    op.drop_constraint("edges_workspace_id_fkey", "edges", type_="foreignkey")
    op.create_foreign_key("edges_workspace_id_fkey", "edges", "workspaces",
                          ["workspace_id"], ["id"])
    op.drop_constraint("nodes_workspace_id_fkey", "nodes", type_="foreignkey")
    op.create_foreign_key("nodes_workspace_id_fkey", "nodes", "workspaces",
                          ["workspace_id"], ["id"])
    op.drop_constraint("users_workspace_id_fkey", "users", type_="foreignkey")
    op.create_foreign_key("users_workspace_id_fkey", "users", "workspaces",
                          ["workspace_id"], ["id"])
