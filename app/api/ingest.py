from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.database import get_db
from app.models.schemas import IngestionRequest, IngestionUploadResponse
from app.models.db import Workspace, Node, Edge, EdgeType, NodeStatus, AuditLog, AuditAction, new_uuid
from app.agents.ingestor import IngestorAgent
from app.agents.structurer import StructurerAgent
from app.agents.linker import LinkerAgent
from app.storage.bundle import BundleManager
from app.config import settings
from app.auth.deps import require_role
from app.llm import get_llm_client
from app.ingestion import detect_format, parse_document

router = APIRouter(prefix="/v1/ingest", tags=["Ingestion"])


async def _run_pipeline(
    workspace_id: str,
    sections: List[dict],
    filename: Optional[str],
    source_type: Optional[str],
    db: AsyncSession,
    llm,
) -> dict:
    bundle = BundleManager(settings.okf_bundle_root, workspace_id)
    structurer = StructurerAgent(llm_client=llm)
    linker = LinkerAgent(bundle, llm_client=llm)

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
                workspace_id=workspace_id,
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
            workspace_id=workspace_id,
            action=AuditAction.ingest,
            resource_type="document",
            details={
                "filename": filename,
                "sections": len(sections),
                "source_type": source_type,
            },
        )
        db.add(audit)

        await db.flush()

        for concept_path, linked_paths in concept_links:
            if not linked_paths:
                continue
            src_result = await db.execute(
                select(Node).where(
                    Node.workspace_id == workspace_id,
                    Node.concept_path == concept_path,
                )
            )
            src_node = src_result.scalar_one_or_none()
            if not src_node:
                continue
            for tgt_path in linked_paths:
                tgt_result = await db.execute(
                    select(Node).where(
                        Node.workspace_id == workspace_id,
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
                    workspace_id=workspace_id,
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
        raise

    return {
        "status": "ok",
        "workspace_id": workspace_id,
        "concepts_created": len(sections),
    }


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

    ingestor = IngestorAgent(llm_client=llm)
    sections = await ingestor.process(
        content=req.content,
        filename=req.filename,
        source_type=req.source_type,
    )

    return await _run_pipeline(
        workspace_id=req.workspace_id,
        sections=sections,
        filename=req.filename,
        source_type=req.source_type,
        db=db,
        llm=llm,
    )


@router.post("/upload", response_model=IngestionUploadResponse)
async def ingest_upload(
    workspace_id: str = Query(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor"])),
    llm=Depends(get_llm_client),
):
    ws_result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    if not ws_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Workspace not found")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        mime_hint = file.content_type or ""
        parsed = parse_document(data, filename=file.filename or "", mime_hint=mime_hint)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    ingestor = IngestorAgent(llm_client=llm)
    sections = await ingestor.process(
        content="\n\n".join(s.text for s in parsed.sections),
        filename=file.filename,
        source_type=parsed.source_type,
    )

    result = await _run_pipeline(
        workspace_id=workspace_id,
        sections=sections,
        filename=file.filename,
        source_type=parsed.source_type,
        db=db,
        llm=llm,
    )

    return IngestionUploadResponse(
        status=result["status"],
        workspace_id=result["workspace_id"],
        filename=file.filename or "unknown",
        source_type=parsed.source_type,
        concepts_created=result["concepts_created"],
        sections=len(sections),
    )
