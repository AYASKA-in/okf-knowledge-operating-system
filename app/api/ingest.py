from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models.schemas import IngestionRequest, ConceptResponse
from app.models.db import Workspace, Node, Edge, EdgeType, NodeStatus, AuditLog, AuditAction, new_uuid
from app.agents.ingestor import IngestorAgent
from app.agents.structurer import StructurerAgent
from app.agents.linker import LinkerAgent
from app.storage.bundle import BundleManager
from app.config import settings
from app.auth.deps import require_role
from app.llm import get_llm_client

router = APIRouter(prefix="/v1/ingest", tags=["Ingestion"])


@router.post("")
async def ingest_document(
    req: IngestionRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor"])),
    llm=Depends(get_llm_client),
):
    result = await db.execute(select(Workspace).where(Workspace.id == req.workspace_id))
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    bundle = BundleManager(settings.okf_bundle_root, req.workspace_id)
    ingestor = IngestorAgent(llm_client=llm)
    structurer = StructurerAgent(llm_client=llm)
    linker = LinkerAgent(bundle, llm_client=llm)

    sections = await ingestor.process(
        content=req.content,
        filename=req.filename,
        source_type=req.source_type,
    )

    written_paths = []
    concept_links = []

    try:
        for section in sections:
            concept = await structurer.generate_concept(section, base_path="ingested")
            linked_concept, linked_paths = await linker.link_concept(concept)

            bundle.write_concept(linked_concept)
            written_paths.append(linked_concept.filepath)
            concept_links.append((linked_concept.filepath, linked_paths))

            node = Node(
                workspace_id=req.workspace_id,
                concept_path=linked_concept.filepath,
                title=linked_concept.frontmatter.title or "",
                node_type=linked_concept.frontmatter.type,
                tags=linked_concept.frontmatter.tags or [],
                status=NodeStatus.draft,
                source_hash=section.get("hash", ""),
                file_size=len(linked_concept.body),
                body_text=linked_concept.body or "",
            )
            db.add(node)

        audit = AuditLog(
            workspace_id=req.workspace_id,
            action=AuditAction.ingest,
            resource_type="document",
            details={
                "filename": req.filename,
                "sections": len(sections),
                "source_type": req.source_type,
            },
        )
        db.add(audit)

        await db.flush()

        for concept_path, linked_paths in concept_links:
            if not linked_paths:
                continue
            src_result = await db.execute(
                select(Node).where(
                    Node.workspace_id == req.workspace_id,
                    Node.concept_path == concept_path,
                )
            )
            src_node = src_result.scalar_one_or_none()
            if not src_node:
                continue
            for tgt_path in linked_paths:
                tgt_result = await db.execute(
                    select(Node).where(
                        Node.workspace_id == req.workspace_id,
                        Node.concept_path == tgt_path,
                    )
                )
                tgt_node = tgt_result.scalar_one_or_none()
                if not tgt_node or tgt_node.id == src_node.id:
                    continue
                existing = await db.execute(
                    select(Edge).where(
                        Edge.source_id == src_node.id,
                        Edge.target_id == tgt_node.id,
                        Edge.edge_type == EdgeType.references,
                    )
                )
                if existing.scalar_one_or_none():
                    continue
                edge = Edge(
                    id=new_uuid(),
                    workspace_id=req.workspace_id,
                    source_id=src_node.id,
                    target_id=tgt_node.id,
                    edge_type=EdgeType.references,
                )
                db.add(edge)

        await db.flush()

    except Exception as e:
        for path in written_paths:
            try:
                bundle.delete_concept(path)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")

    return {
        "status": "ok",
        "workspace_id": req.workspace_id,
        "concepts_created": len(sections),
    }
