from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List

from app.database import get_db
from app.models.schemas import EdgeCreate, EdgeResponse
from app.models.db import Edge, EdgeType, Node, new_uuid
from app.config import settings
from app.auth.deps import require_role

router = APIRouter(tags=["Edges"])


@router.post("/v1/edges", response_model=EdgeResponse, status_code=201)
async def create_edge(
    edge: EdgeCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor"])),
):
    try:
        edge_type = EdgeType(edge.edge_type)
    except ValueError:
        valid = [e.value for e in EdgeType]
        raise HTTPException(status_code=400, detail=f"Invalid edge_type. Must be one of: {valid}")

    source = await db.get(Node, edge.source_id)
    if not source or source.workspace_id != edge.workspace_id:
        raise HTTPException(status_code=404, detail="Source concept not found")
    target = await db.get(Node, edge.target_id)
    if not target or target.workspace_id != edge.workspace_id:
        raise HTTPException(status_code=404, detail="Target concept not found")

    existing = await db.execute(
        select(Edge).where(
            Edge.source_id == edge.source_id,
            Edge.target_id == edge.target_id,
            Edge.edge_type == edge_type,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Edge already exists between these concepts")

    row = Edge(
        id=new_uuid(),
        workspace_id=edge.workspace_id,
        source_id=edge.source_id,
        target_id=edge.target_id,
        edge_type=edge_type,
        edge_metadata=edge.metadata,
    )
    db.add(row)
    await db.flush()

    return EdgeResponse(
        id=row.id,
        workspace_id=row.workspace_id,
        source_id=row.source_id,
        target_id=row.target_id,
        edge_type=row.edge_type.value,
        metadata=row.edge_metadata or {},
        created_at=row.created_at,
    )


@router.get("/v1/knowledge/{concept_id}/edges", response_model=List[EdgeResponse])
async def get_concept_edges(
    concept_id: str,
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor", "viewer"])),
):
    node = await db.get(Node, concept_id)
    if not node or node.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Concept not found")

    result = await db.execute(
        select(Edge).where(
            Edge.workspace_id == workspace_id,
            or_(Edge.source_id == concept_id, Edge.target_id == concept_id),
        ).order_by(Edge.created_at.desc())
    )
    edges = result.scalars().all()

    return [
        EdgeResponse(
            id=e.id,
            workspace_id=e.workspace_id,
            source_id=e.source_id,
            target_id=e.target_id,
            edge_type=e.edge_type.value,
            metadata=e.edge_metadata or {},
            created_at=e.created_at,
        )
        for e in edges
    ]


@router.delete("/v1/edges/{edge_id}")
async def delete_edge(
    edge_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor"])),
):
    result = await db.execute(select(Edge).where(Edge.id == edge_id))
    edge = result.scalar_one_or_none()
    if not edge:
        raise HTTPException(status_code=404, detail="Edge not found")

    await db.delete(edge)
    return {"status": "ok", "deleted": edge_id}
