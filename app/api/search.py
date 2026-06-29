from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, String
from sqlalchemy.sql import text
from typing import List, Optional

from app.database import get_db
from app.models.schemas import SearchRequest, SearchResult
from app.models.db import Workspace, Node, NodeStatus, Edge
from app.config import settings
from app.auth.deps import require_role

router = APIRouter(prefix="/v1/search", tags=["Search"])


@router.post("", response_model=List[SearchResult])
async def search_concepts(
    req: SearchRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor", "viewer"])),
    response: Response = None,
):
    ws_result = await db.execute(select(Workspace).where(Workspace.id == req.workspace_id))
    if not ws_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Workspace not found")

    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    tsquery = " & ".join(query.split())

    inbound_edge_count = (
        select(func.count(Edge.id))
        .where(Edge.target_id == Node.id)
        .correlate(Node)
        .scalar_subquery()
    )

    try:
        ts_match = func.to_tsvector("english", Node.body_text).op("@@")(func.to_tsquery("english", tsquery))
        base_filters = [Node.workspace_id == req.workspace_id, ts_match]

        if req.type_filter:
            base_filters.append(Node.node_type == req.type_filter)
        if req.tag:
            base_filters.append(Node.tags.cast(String).contains(req.tag))

        count_stmt = select(func.count()).select_from(
            select(Node).where(*base_filters).subquery()
        )
        total = await db.scalar(count_stmt) or 0
        if response is not None:
            response.headers["X-Total-Count"] = str(total)

        search_stmt = select(
            Node,
            (
                func.ts_rank(
                    func.to_tsvector("english", Node.body_text),
                    func.to_tsquery("english", tsquery),
                ) + func.coalesce(inbound_edge_count, 0) * 0.1
            ).label("rank"),
        ).where(*base_filters)

        search_stmt = search_stmt.order_by(text("rank DESC"))
        search_stmt = search_stmt.offset(req.offset).limit(req.limit)

        result = await db.execute(search_stmt)
        rows = result.all()
    except Exception:
        import traceback
        traceback.print_exc()
        query_lower = query.lower()
        fb_filters = [
            Node.workspace_id == req.workspace_id,
            or_(
                func.lower(Node.title).contains(query_lower),
                func.lower(Node.body_text).contains(query_lower),
            ),
        ]
        if req.tag:
            fb_filters.append(Node.tags.cast(String).contains(req.tag))
        if req.type_filter:
            fb_filters.append(Node.node_type == req.type_filter)

        count_fb = select(func.count()).select_from(
            select(Node).where(*fb_filters).subquery()
        )
        total = await db.scalar(count_fb) or 0
        if response is not None:
            response.headers["X-Total-Count"] = str(total)

        stmt = select(
            Node,
            func.coalesce(inbound_edge_count, 0).label("rank"),
        ).where(*fb_filters)
        stmt = stmt.order_by(text("rank DESC"), Node.updated_at.desc())
        stmt = stmt.offset(req.offset).limit(req.limit)
        result = await db.execute(stmt)
        rows = result.all()

    responses = []
    for node, rank in rows:
        body_lower = (node.body_text or "").lower()
        query_lower = query.lower()
        idx = body_lower.find(query_lower)
        if idx >= 0:
            start = max(0, idx - 60)
            end = min(len(node.body_text or ""), idx + len(query) + 60)
            snippet = (node.body_text or "")[start:end]
            if start > 0:
                snippet = "..." + snippet
            if end < len(node.body_text or ""):
                snippet = snippet + "..."
        else:
            snippet = (node.body_text or "")[:200]

        responses.append(SearchResult(
            id=node.id,
            filepath=node.concept_path,
            title=node.title,
            type=node.node_type,
            tags=list(node.tags or []),
            status=node.status.value,
            snippet=snippet,
            score=float(rank),
            created_at=node.created_at,
            updated_at=node.updated_at,
        ))

    return responses
