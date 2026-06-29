from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List, Set

from app.database import get_db
from app.models.schemas import SubgraphResponse, GraphNode, GraphEdge, PathRequest, PathResponse
from app.models.db import Node, Edge
from app.auth.deps import require_role

router = APIRouter(tags=["Graph"])


@router.get("/v1/knowledge/{concept_id}/graph", response_model=SubgraphResponse)
async def get_concept_subgraph(
    concept_id: str,
    workspace_id: str = Query(...),
    depth: int = Query(1, ge=1, le=5),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor", "viewer"])),
):
    node = await db.get(Node, concept_id)
    if not node or node.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Concept not found")

    visited_ids: Set[str] = {concept_id}
    frontier: Set[str] = {concept_id}
    collected_nodes: List[GraphNode] = []
    collected_edges: List[GraphEdge] = []
    seen_edges: Set[str] = set()
    node_map: dict = {}

    for _ in range(depth):
        if not frontier:
            break

        edge_result = await db.execute(
            select(Edge).where(
                Edge.workspace_id == workspace_id,
                or_(Edge.source_id.in_(frontier), Edge.target_id.in_(frontier)),
            )
        )
        edges = edge_result.scalars().all()

        next_frontier: Set[str] = set()
        for e in edges:
            edge_key = f"{e.source_id}→{e.target_id}→{e.edge_type.value}"
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                collected_edges.append(GraphEdge(source=e.source_id, target=e.target_id, type=e.edge_type.value))
            if e.source_id not in visited_ids:
                next_frontier.add(e.source_id)
            if e.target_id not in visited_ids:
                next_frontier.add(e.target_id)

        visited_ids |= next_frontier
        if next_frontier:
            node_result = await db.execute(
                select(Node).where(Node.id.in_(next_frontier))
            )
            for n in node_result.scalars().all():
                if n.id not in node_map:
                    node_map[n.id] = n
                    collected_nodes.append(GraphNode(id=n.id, label=n.title or n.concept_path, type=n.node_type, filepath=n.concept_path))

        frontier = next_frontier

    seed = node
    collected_nodes.insert(0, GraphNode(id=seed.id, label=seed.title or seed.concept_path, type=seed.node_type, filepath=seed.concept_path))

    return SubgraphResponse(nodes=collected_nodes, edges=collected_edges)


@router.post("/v1/graph/path", response_model=PathResponse)
async def find_graph_path(
    req: PathRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor", "viewer"])),
):
    source = await db.get(Node, req.source_id)
    if not source or source.workspace_id != req.workspace_id:
        raise HTTPException(status_code=404, detail="Source concept not found")
    target = await db.get(Node, req.target_id)
    if not target or target.workspace_id != req.workspace_id:
        raise HTTPException(status_code=404, detail="Target concept not found")

    if req.source_id == req.target_id:
        n = GraphNode(id=source.id, label=source.title or source.concept_path, type=source.node_type, filepath=source.concept_path)
        return PathResponse(nodes=[n], edges=[], path_found=True)

    visited: Set[str] = {req.source_id}
    parent: dict = {}
    queue: List[str] = [req.source_id]
    found = False

    while queue and not found:
        current = queue.pop(0)
        edge_result = await db.execute(
            select(Edge).where(
                Edge.workspace_id == req.workspace_id,
                or_(Edge.source_id == current, Edge.target_id == current),
            )
        )
        for e in edge_result.scalars().all():
            neighbor = e.target_id if e.source_id == current else e.source_id
            if neighbor not in visited:
                visited.add(neighbor)
                parent[neighbor] = (current, e)
                if neighbor == req.target_id:
                    found = True
                    break
                queue.append(neighbor)

    if not found:
        src_n = GraphNode(id=source.id, label=source.title or source.concept_path, type=source.node_type, filepath=source.concept_path)
        tgt_n = GraphNode(id=target.id, label=target.title or target.concept_path, type=target.node_type, filepath=target.concept_path)
        return PathResponse(nodes=[src_n, tgt_n], edges=[], path_found=False)

    path_edges: List[GraphEdge] = []
    path_node_ids: Set[str] = {req.target_id}
    cur = req.target_id
    while cur in parent:
        prev, edge = parent[cur]
        path_edges.append(GraphEdge(source=prev, target=cur, type=edge.edge_type.value))
        path_node_ids.add(prev)
        cur = prev

    path_edges.reverse()
    node_result = await db.execute(
        select(Node).where(Node.id.in_(path_node_ids))
    )
    node_map = {n.id: n for n in node_result.scalars().all()}
    path_nodes = [GraphNode(id=n_id, label=node_map[n_id].title or node_map[n_id].concept_path, type=node_map[n_id].node_type, filepath=node_map[n_id].concept_path) for n_id in path_node_ids]

    return PathResponse(nodes=path_nodes, edges=path_edges, path_found=True)
