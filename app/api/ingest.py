from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.database import get_db, get_session_factory
from app.models.schemas import (
    IngestionRequest, IngestionUploadResponse,
    IngestJobResponse, IngestJobCreateResponse,
)
from app.models.db import (
    Workspace, Node, Edge, EdgeType, NodeStatus, AuditLog, AuditAction,
    IngestJob, IngestJobStatus, new_uuid,
)
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

    return {
        "status": "ok",
        "workspace_id": workspace_id,
        "concepts_created": len(sections),
    }


async def _background_ingest(
    job_id: str,
    workspace_id: str,
    sections: List[dict],
    filename: Optional[str],
    source_type: Optional[str],
    llm,
):
    """Run ingest pipeline in background, updating job status as we go."""
    factory = get_session_factory()
    async with factory() as db:
        try:
            job_result = await db.execute(select(IngestJob).where(IngestJob.id == job_id))
            job = job_result.scalar_one_or_none()
            if not job:
                return

            job.status = IngestJobStatus.running
            job.progress_pct = 5
            await db.commit()

            result = await _run_pipeline(
                workspace_id=workspace_id,
                sections=sections,
                filename=filename,
                source_type=source_type,
                db=db,
                llm=llm,
            )

            job.status = IngestJobStatus.done
            job.progress_pct = 100
            job.result_summary = result
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()

        except Exception as exc:
            try:
                job_result = await db.execute(select(IngestJob).where(IngestJob.id == job_id))
                job = job_result.scalar_one_or_none()
                if job:
                    job.status = IngestJobStatus.failed
                    job.error_message = str(exc)[:2000]
                    job.completed_at = datetime.now(timezone.utc)
                    await db.commit()
            except Exception:
                pass


def _sections_from_content(content: str, filename: Optional[str], source_type: Optional[str], llm) -> List[dict]:
    """Synchronous wrapper — actually runs async via the callers."""
    raise RuntimeError("Use _prepare_sections_for_background instead")


async def _prepare_sections_for_background(
    content: str,
    filename: Optional[str],
    source_type: Optional[str],
    llm,
) -> List[dict]:
    ingestor = IngestorAgent(llm_client=llm)
    return await ingestor.process(
        content=content,
        filename=filename,
        source_type=source_type,
    )


@router.post("", response_model=IngestJobCreateResponse)
async def ingest_document(
    req: IngestionRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor"])),
    llm=Depends(get_llm_client),
):
    ws_result = await db.execute(select(Workspace).where(Workspace.id == req.workspace_id))
    if not ws_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Workspace not found")

    job = IngestJob(
        id=new_uuid(),
        workspace_id=req.workspace_id,
        filename=req.filename or "direct_input",
        source_type=req.source_type or "text",
        status=IngestJobStatus.pending,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    sections = await _prepare_sections_for_background(
        content=req.content,
        filename=req.filename,
        source_type=req.source_type,
        llm=llm,
    )

    background_tasks.add_task(
        _background_ingest,
        job_id=job.id,
        workspace_id=req.workspace_id,
        sections=sections,
        filename=req.filename,
        source_type=req.source_type,
        llm=llm,
    )

    return IngestJobCreateResponse(job_id=job.id, status=job.status.value)


@router.post("/upload", response_model=IngestJobCreateResponse)
async def ingest_upload(
    workspace_id: str = Query(...),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
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

    content = "\n\n".join(s.text for s in parsed.sections)

    job = IngestJob(
        id=new_uuid(),
        workspace_id=workspace_id,
        filename=file.filename or "unknown",
        source_type=parsed.source_type,
        status=IngestJobStatus.pending,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    sections = await _prepare_sections_for_background(
        content=content,
        filename=file.filename,
        source_type=parsed.source_type,
        llm=llm,
    )

    background_tasks.add_task(
        _background_ingest,
        job_id=job.id,
        workspace_id=workspace_id,
        sections=sections,
        filename=file.filename,
        source_type=parsed.source_type,
        llm=llm,
    )

    return IngestJobCreateResponse(job_id=job.id, status=job.status.value)


@router.get("/jobs/{job_id}", response_model=IngestJobResponse)
async def get_ingest_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor", "viewer"])),
):
    result = await db.execute(select(IngestJob).where(IngestJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Ingest job not found")

    return IngestJobResponse(
        id=job.id,
        workspace_id=job.workspace_id,
        filename=job.filename,
        source_type=job.source_type,
        status=job.status.value,
        progress_pct=job.progress_pct,
        error_message=job.error_message or "",
        result_summary=job.result_summary or {},
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
    )


@router.get("/jobs", response_model=List[IngestJobResponse])
async def list_ingest_jobs(
    workspace_id: str = Query(...),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor", "viewer"])),
):
    query = select(IngestJob).where(IngestJob.workspace_id == workspace_id)
    if status:
        try:
            status_val = IngestJobStatus(status)
            query = query.where(IngestJob.status == status_val)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {[s.value for s in IngestJobStatus]}")

    query = query.order_by(IngestJob.created_at.desc()).limit(limit)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return [
        IngestJobResponse(
            id=j.id,
            workspace_id=j.workspace_id,
            filename=j.filename,
            source_type=j.source_type,
            status=j.status.value,
            progress_pct=j.progress_pct,
            error_message=j.error_message or "",
            result_summary=j.result_summary or {},
            created_at=j.created_at,
            updated_at=j.updated_at,
            completed_at=j.completed_at,
        )
        for j in jobs
    ]


@router.post("/jobs/{job_id}/retry", response_model=IngestJobCreateResponse)
async def retry_ingest_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor"])),
    llm=Depends(get_llm_client),
):
    result = await db.execute(select(IngestJob).where(IngestJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Ingest job not found")
    if job.status != IngestJobStatus.failed:
        raise HTTPException(status_code=400, detail="Only failed jobs can be retried")

    new_job = IngestJob(
        id=new_uuid(),
        workspace_id=job.workspace_id,
        filename=job.filename,
        source_type=job.source_type,
        status=IngestJobStatus.pending,
    )
    db.add(new_job)
    await db.commit()
    await db.refresh(new_job)

    bundle = BundleManager(settings.okf_bundle_root, job.workspace_id)
    concepts = bundle.list_concepts()
    content_lines = []
    for cp in concepts:
        try:
            c = bundle.read_concept(cp)
            content_lines.append(f"# {c.frontmatter.title or cp}\n\n{c.body}")
        except Exception:
            pass
    content = "\n\n".join(content_lines) if content_lines else ""

    sections = await _prepare_sections_for_background(
        content=content or "retry",
        filename=job.filename,
        source_type=job.source_type,
        llm=llm,
    )

    background_tasks.add_task(
        _background_ingest,
        job_id=new_job.id,
        workspace_id=job.workspace_id,
        sections=sections,
        filename=job.filename,
        source_type=job.source_type,
        llm=llm,
    )

    return IngestJobCreateResponse(job_id=new_job.id, status=new_job.status.value)
