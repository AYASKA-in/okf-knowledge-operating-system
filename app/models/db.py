import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, Enum,
    ForeignKey, JSON, Index, UniqueConstraint, TypeDecorator, types,
)
from sqlalchemy.orm import relationship
import enum
from app.database import Base


class StringArray(TypeDecorator):
    """Stores list-of-strings; uses ARRAY(String) on PostgreSQL, JSON elsewhere."""
    impl = types.JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import ARRAY
            return dialect.type_descriptor(ARRAY(types.String))
        return dialect.type_descriptor(types.JSON())


def utcnow():
    return datetime.now(timezone.utc)


def new_uuid():
    return str(uuid.uuid4())


class NodeStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class EdgeType(str, enum.Enum):
    references = "references"
    depends_on = "depends_on"
    parent_of = "parent_of"
    related_to = "related_to"


class IngestJobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class AuditAction(str, enum.Enum):
    query = "query"
    chat = "chat"
    approve = "approve"
    reject = "reject"
    export = "export"
    delete = "delete"
    ingest = "ingest"


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        Index("ix_workspaces_name", "name"),
    )

    id = Column(String, primary_key=True, default=new_uuid)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, default="")
    bucket_path = Column(String(512), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    users = relationship("User", back_populates="workspace")
    nodes = relationship("Node", back_populates="workspace")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_workspace_id", "workspace_id"),
    )

    id = Column(String, primary_key=True, default=new_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(320), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=False)
    role = Column(String(50), default="viewer")
    attributes = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    workspace = relationship("Workspace", back_populates="users")


class Node(Base):
    __tablename__ = "nodes"
    __table_args__ = (
        UniqueConstraint("workspace_id", "concept_path", name="uq_node_workspace_path"),
        Index("ix_nodes_workspace_id", "workspace_id"),
        Index("ix_nodes_node_type", "workspace_id", "node_type"),
        Index("ix_nodes_status", "workspace_id", "status"),
        Index("ix_nodes_updated_at", "workspace_id", "updated_at"),
    )

    id = Column(String, primary_key=True, default=new_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    concept_path = Column(String(1024), nullable=False)
    title = Column(String(512), default="")
    node_type = Column(String(100), nullable=False)
    tags = Column(StringArray(), default=list)
    status = Column(Enum(NodeStatus), default=NodeStatus.draft)
    source_hash = Column(String(64), default="")
    source_connector = Column(String(50), nullable=True)
    source_original_id = Column(String(255), nullable=True)
    chunk_index = Column(Integer, nullable=True)
    parent_hash = Column(String(64), nullable=True)
    token_count = Column(Integer, nullable=True)
    file_size = Column(Integer, default=0)
    body_text = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    workspace = relationship("Workspace", back_populates="nodes")
    edges_out = relationship("Edge", foreign_keys="Edge.source_id", back_populates="source",
                             cascade="all, delete-orphan")
    edges_in = relationship("Edge", foreign_keys="Edge.target_id", back_populates="target",
                            cascade="all, delete-orphan")


class Edge(Base):
    __tablename__ = "edges"
    __table_args__ = (
        Index("ix_edges_workspace_id", "workspace_id"),
        Index("ix_edges_source", "source_id"),
        Index("ix_edges_target", "target_id"),
        UniqueConstraint("source_id", "target_id", "edge_type", name="uq_edge_pair"),
    )

    id = Column(String, primary_key=True, default=new_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    source_id = Column(String, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(String, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False)
    edge_type = Column(Enum(EdgeType), default=EdgeType.references)
    edge_metadata = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    source = relationship("Node", foreign_keys=[source_id], back_populates="edges_out")
    target = relationship("Node", foreign_keys=[target_id], back_populates="edges_in")


class IngestJob(Base):
    __tablename__ = "ingest_jobs"
    __table_args__ = (
        Index("ix_ingest_jobs_workspace_id", "workspace_id"),
        Index("ix_ingest_jobs_status", "workspace_id", "status"),
        Index("ix_ingest_jobs_created_at", "workspace_id", "created_at"),
    )

    id = Column(String, primary_key=True, default=new_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(512), default="")
    source_type = Column(String(50), default="")
    status = Column(Enum(IngestJobStatus), default=IngestJobStatus.pending)
    progress_pct = Column(Integer, default=0)
    error_message = Column(Text, default="")
    result_summary = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class ExportJobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class ExportJob(Base):
    __tablename__ = "export_jobs"
    __table_args__ = (
        Index("ix_export_jobs_workspace_id", "workspace_id"),
        Index("ix_export_jobs_status", "workspace_id", "status"),
        Index("ix_export_jobs_created_at", "workspace_id", "created_at"),
    )

    id = Column(String, primary_key=True, default=new_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    status = Column(Enum(ExportJobStatus), default=ExportJobStatus.pending)
    format = Column(String(20), default="zip")
    filename = Column(String(512), default="")
    file_size = Column(Integer, default=0)
    file_path = Column(String(1024), default="")
    error_message = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class ConnectorConfig(Base):
    __tablename__ = "connector_configs"
    __table_args__ = (
        Index("ix_connector_configs_workspace_id", "workspace_id"),
        UniqueConstraint("workspace_id", "connector_type", name="uq_connector_workspace_type"),
    )

    id = Column(String, primary_key=True, default=new_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    connector_type = Column(String(50), nullable=False)
    label = Column(String(255), default="")
    config = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    last_status = Column(String(100), default="")
    last_polled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_workspace_id", "workspace_id"),
        Index("ix_audit_created_at", "workspace_id", "created_at"),
        Index("ix_audit_action", "workspace_id", "action"),
    )

    id = Column(String, primary_key=True, default=new_uuid)
    workspace_id = Column(String, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(Enum(AuditAction), nullable=False)
    resource_type = Column(String(50), default="")
    resource_id = Column(String(100), default="")
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), default="")
    cost_estimate = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow)
