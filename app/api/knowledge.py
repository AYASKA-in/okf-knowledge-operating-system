from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import List, Optional

from app.database import get_db
from app.models.schemas import ConceptCreate, ConceptResponse, ConceptListItem, ConceptUpdate
from app.models.db import Node, NodeStatus, Edge, EdgeType, new_uuid
from app.models.okf import OKFConcept, OKFFrontmatter
from app.storage.bundle import BundleManager
from app.config import settings
from app.auth.deps import require_role
from app.agents.linker import LinkerAgent
from app.llm import get_llm_client

router = APIRouter(prefix="/v1/knowledge", tags=["Knowledge"])


@router.get("/{concept_id}", response_model=ConceptResponse)
async def get_concept(
    concept_id: str,
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor", "viewer"])),
):
    result = await db.execute(
        select(Node).where(Node.id == concept_id, Node.workspace_id == workspace_id)
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Concept not found")

    bundle = BundleManager(settings.okf_bundle_root, workspace_id)
    concept_body = ""
    try:
        concept = bundle.read_concept(node.concept_path)
        concept_body = concept.body
    except Exception:
        pass

    return ConceptResponse(
        id=node.id,
        filepath=node.concept_path,
        title=node.title,
        type=node.node_type,
        tags=list(node.tags or []),
        status=node.status.value,
        body=concept_body,
        created_at=node.created_at,
        updated_at=node.updated_at,
    )


@router.get("", response_model=List[ConceptListItem])
async def list_concepts(
    workspace_id: str = Query(...),
    type_filter: Optional[str] = Query(None, alias="type"),
    tag: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor", "viewer"])),
    response: Response = None,
):
    query = select(Node).where(Node.workspace_id == workspace_id)

    if type_filter:
        query = query.where(Node.node_type == type_filter)
    if tag:
        query = query.where(Node.tags.any(tag))
    if status:
        valid_statuses = {s.value for s in NodeStatus}
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        query = query.where(Node.status == status)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)
    if response is not None:
        response.headers["X-Total-Count"] = str(total)

    result = await db.execute(
        query.order_by(Node.updated_at.desc()).offset(offset).limit(limit)
    )
    nodes = result.scalars().all()

    return [
        ConceptListItem(
            id=n.id,
            filepath=n.concept_path,
            title=n.title,
            type=n.node_type,
            tags=list(n.tags or []),
            status=n.status.value,
            created_at=n.created_at,
            updated_at=n.updated_at,
        )
        for n in nodes
    ]


@router.post("", response_model=ConceptResponse, status_code=201)
async def create_concept(
    concept: ConceptCreate,
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor"])),
    llm=Depends(get_llm_client),
):
    node_id = new_uuid()
    safe_title = concept.title or concept.type
    concept_path = safe_title.lower().replace(" ", "_") + ".md"

    existing = await db.execute(
        select(Node).where(Node.workspace_id == workspace_id, Node.concept_path == concept_path)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Concept with this path already exists")

    bundle = BundleManager(settings.okf_bundle_root, workspace_id)

    frontmatter = OKFFrontmatter(
        type=concept.type,
        title=concept.title,
        description=concept.description,
        tags=concept.tags,
        status=concept.status or "draft",
    )
    okf_concept = OKFConcept(filepath=concept_path, frontmatter=frontmatter, body=concept.body)
    bundle.write_concept(okf_concept)

    linker = LinkerAgent(bundle, llm_client=llm)
    linked_concept, linked_paths = await linker.link_concept(okf_concept)

    if linked_paths:
        bundle.write_concept(linked_concept)
        body = linked_concept.body
    else:
        body = concept.body

    status_val = NodeStatus(concept.status) if concept.status else NodeStatus.draft

    node = Node(
        id=node_id,
        workspace_id=workspace_id,
        concept_path=concept_path,
        title=concept.title or "",
        node_type=concept.type,
        tags=concept.tags or [],
        status=status_val,
        body_text=body,
    )
    db.add(node)
    await db.flush()

    for tgt_path in linked_paths:
        tgt_result = await db.execute(
            select(Node).where(
                Node.workspace_id == workspace_id,
                Node.concept_path == tgt_path,
            )
        )
        tgt_node = tgt_result.scalar_one_or_none()
        if not tgt_node or tgt_node.id == node.id:
            continue
        existing_edge = await db.execute(
            select(Edge).where(
                Edge.source_id == node.id,
                Edge.target_id == tgt_node.id,
                Edge.edge_type == EdgeType.references,
            )
        )
        if existing_edge.scalar_one_or_none():
            continue
        edge = Edge(
            id=new_uuid(),
            workspace_id=workspace_id,
            source_id=node.id,
            target_id=tgt_node.id,
            edge_type=EdgeType.references,
        )
        db.add(edge)

    await db.flush()

    return ConceptResponse(
        id=node.id,
        filepath=node.concept_path,
        title=node.title,
        type=node.node_type,
        tags=list(node.tags or []),
        status=node.status.value,
        body=body,
        created_at=node.created_at,
        updated_at=node.updated_at,
    )


@router.put("/{concept_id}", response_model=ConceptResponse)
async def update_concept(
    concept_id: str,
    update: ConceptUpdate,
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor"])),
):
    result = await db.execute(
        select(Node).where(Node.id == concept_id, Node.workspace_id == workspace_id)
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Concept not found")

    bundle = BundleManager(settings.okf_bundle_root, workspace_id)

    concept = None
    if update.body is not None or update.type is not None or update.title is not None:
        try:
            concept = bundle.read_concept(node.concept_path)
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to read concept file for update")

        if update.type is not None:
            concept.frontmatter.type = update.type
            node.node_type = update.type
        if update.title is not None:
            concept.frontmatter.title = update.title
            node.title = update.title
        if update.description is not None:
            concept.frontmatter.description = update.description
        if update.tags is not None:
            concept.frontmatter.tags = update.tags
            node.tags = update.tags
        if update.status is not None:
            concept.frontmatter.status = update.status
            try:
                node.status = NodeStatus(update.status)
            except ValueError:
                pass
        if update.body is not None:
            concept.body = update.body
            node.body_text = update.body

        bundle.write_concept(concept)

    return ConceptResponse(
        id=node.id,
        filepath=node.concept_path,
        title=node.title,
        type=node.node_type,
        tags=list(node.tags or []),
        status=node.status.value,
        body=concept.body if concept else "",
        created_at=node.created_at,
        updated_at=node.updated_at,
    )


@router.delete("/{concept_id}")
async def delete_concept(
    concept_id: str,
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor"])),
):
    result = await db.execute(
        select(Node).where(Node.id == concept_id, Node.workspace_id == workspace_id)
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Concept not found")

    bundle = BundleManager(settings.okf_bundle_root, workspace_id)
    bundle.delete_concept(node.concept_path)

    await db.delete(node)
    return {"status": "ok", "deleted": concept_id}


@router.post("/{concept_id}/links")
async def get_concept_links(
    concept_id: str,
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor", "viewer"])),
):
    result = await db.execute(
        select(Node).where(Node.id == concept_id, Node.workspace_id == workspace_id)
    )
    node = result.scalar_one_or_none()
    if not node:
        raise HTTPException(status_code=404, detail="Concept not found")

    bundle = BundleManager(settings.okf_bundle_root, workspace_id)
    resolved = bundle.resolve_links(node.concept_path)

    edges_result = await db.execute(
        select(Edge).where(
            or_(Edge.source_id == concept_id, Edge.target_id == concept_id)
        )
    )
    edges = edges_result.scalars().all()
    edge_targets = [
        {"edge_type": e.edge_type.value,
         "source_id": e.source_id, "target_id": e.target_id}
        for e in edges
    ]

    return {"filepath": node.concept_path, "markdown_links": resolved, "edges": edge_targets}
