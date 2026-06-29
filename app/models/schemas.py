from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ConceptCreate(BaseModel):
    type: str
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    body: str = ""
    status: Optional[str] = "draft"


class ConceptUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    type: Optional[str] = None
    body: Optional[str] = None
    status: Optional[str] = None


class ConceptResponse(BaseModel):
    id: str
    filepath: str
    title: Optional[str] = None
    type: str
    tags: List[str] = []
    status: str
    body: str
    created_at: datetime
    updated_at: datetime


class ConceptListItem(BaseModel):
    id: str
    filepath: str
    title: Optional[str] = None
    type: str
    tags: List[str] = []
    status: str
    created_at: datetime
    updated_at: datetime


class SearchRequest(BaseModel):
    workspace_id: str
    query: str
    type_filter: Optional[str] = None
    tag: Optional[str] = None
    offset: int = 0
    limit: int = 20


class SearchResult(BaseModel):
    id: str
    filepath: str
    title: Optional[str] = None
    type: str
    tags: List[str] = []
    status: str
    snippet: str
    score: float
    created_at: datetime
    updated_at: datetime


class IngestionRequest(BaseModel):
    workspace_id: str
    filename: Optional[str] = None
    content: str
    source_type: Optional[str] = None


class ChatRequest(BaseModel):
    workspace_id: str
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]] = []
    conversation_id: str


class ExportRequest(BaseModel):
    workspace_id: str
    format: str = "zip"


class WorkspaceCreate(BaseModel):
    name: str
    description: Optional[str] = None


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    description: str
    bucket_path: str
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    workspace_id: str
    email: str
    password: str
    display_name: str
    role: str = "viewer"


class UserUpdate(BaseModel):
    email: Optional[str] = None
    display_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: str
    workspace_id: str
    email: str
    display_name: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TokenRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    workspace_id: str
    role: str


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class EdgeCreate(BaseModel):
    workspace_id: str
    source_id: str
    target_id: str
    edge_type: str = "references"
    metadata: Dict[str, Any] = {}


class EdgeResponse(BaseModel):
    id: str
    workspace_id: str
    source_id: str
    target_id: str
    edge_type: str
    metadata: Dict[str, Any] = {}
    created_at: datetime


class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    filepath: str

class GraphEdge(BaseModel):
    source: str
    target: str
    type: str

class SubgraphResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]

class PathRequest(BaseModel):
    workspace_id: str
    source_id: str
    target_id: str

class PathResponse(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    path_found: bool

class TokenData(BaseModel):
    user_id: str
    workspace_id: str
    role: str
    attributes: Dict[str, Any] = {}
