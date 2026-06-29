from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks, Request
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
    IngestJob, IngestJobStatus, ConnectorConfig, new_uuid,
)
from app.storage.bundle import BundleManager
from app.config import settings
from app.auth.deps import require_role
from app.llm import get_llm_client
from app.pipeline import PipelineOrchestrator, PipelineContext
from app.ingestion.router import IngestionRouter

router = APIRouter(prefix="/v1/ingest", tags=["Ingestion"])

INGEST_AUDIT = AuditAction.ingest


async def _run_pipeline(
    workspace_id: str,
    file_data: Optional[bytes],
    content: Optional[str],
    filename: Optional[str],
    source_type: Optional[str],
    db: AsyncSession,
    llm,
    source_connector: Optional[str] = None,
    source_original_id: Optional[str] = None,
) -> dict:
    orchestrator = PipelineOrchestrator(workspace_id, llm_client=llm)
    pctx = PipelineContext()

    pctx.ctx.update({
        "workspace_id": workspace_id,
        "file_data": file_data,
        "filename": filename or "direct_input",
        "mime_hint": source_type or "",
        "source_connector": source_connector,
        "source_original_id": source_original_id,
    })

    if content and not file_data:
        pctx.ctx["raw_markdown"] = content
        pctx.ctx["source_type"] = source_type or "text"

    pctx = await orchestrator.run(pctx)

    parse_result = pctx.results.get("parse")
    chunk_result = pctx.results.get("chunk")
    structure_result = pctx.results.get("structure")
    link_result = pctx.results.get("link")
    embed_result = pctx.results.get("embed")

    if not structure_result or not structure_result.success:
        return {
            "status": "error",
            "workspace_id": workspace_id,
            "concepts_created": 0,
            "duplicates_skipped": 0,
            "pipeline_results": {
                name: {"success": r.success, "error": r.error}
                for name, r in pctx.results.items()
            },
        }

    concepts = structure_result.data.get("concepts", [])
    linked = link_result.data.get("linked_concepts", concepts) if link_result and link_result.success else concepts
    link_map = link_result.data.get("link_map", []) if link_result and link_result.success else []
    sections = chunk_result.data.get("sections", []) if chunk_result and chunk_result.success else []

    bundle = BundleManager(settings.okf_bundle_root, workspace_id)
    written_paths = []
    concept_links = []
    duplicates_skipped = 0

    for i, concept in enumerate(linked):
        section = sections[i] if i < len(sections) else {}
        section_hash = section.get("hash", "")

        if section_hash:
            existing = await db.execute(
                select(Node).where(
                    Node.workspace_id == workspace_id,
                    Node.source_hash == section_hash,
                ).limit(1)
            )
            if existing.scalar_one_or_none():
                duplicates_skipped += 1
                continue

        bundle.write_concept(concept)
        written_paths.append(concept.filepath)

        linked_paths = []
        for fp, paths in link_map:
            if fp == concept.filepath:
                linked_paths = paths
                break
        concept_links.append((concept.filepath, linked_paths))

        node = Node(
            workspace_id=workspace_id,
            concept_path=concept.filepath,
            title=concept.frontmatter.title or "",
            node_type=concept.frontmatter.type,
            tags=concept.frontmatter.tags or [],
            status=NodeStatus.draft,
            source_hash=section_hash,
            source_connector=source_connector,
            source_original_id=source_original_id,
            chunk_index=section.get("chunk_index"),
            parent_hash=section.get("parent_hash"),
            token_count=section.get("tokens_estimate"),
            file_size=len(concept.body),
            body_text=concept.body or "",
        )
        db.add(node)

    total = len(sections) or len(linked)
    audit_details = {
        "filename": filename,
        "sections": total,
        "source_type": source_type,
        "duplicates_skipped": duplicates_skipped,
        "vectors_indexed": embed_result.data.get("vectors_indexed", 0) if embed_result and embed_result.success else 0,
    }
    audit = AuditLog(
        workspace_id=workspace_id,
        action=INGEST_AUDIT,
        resource_type="document",
        details=audit_details,
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
        "concepts_created": total - duplicates_skipped,
        "duplicates_skipped": duplicates_skipped,
        "vectors_indexed": embed_result.data.get("vectors_indexed", 0) if embed_result and embed_result.success else 0,
    }


async def _background_ingest(
    job_id: str,
    workspace_id: str,
    file_data: Optional[bytes],
    content: Optional[str],
    filename: Optional[str],
    source_type: Optional[str],
    llm,
    source_connector: Optional[str] = None,
    source_original_id: Optional[str] = None,
):
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
                file_data=file_data,
                content=content,
                filename=filename,
                source_type=source_type,
                db=db,
                llm=llm,
                source_connector=source_connector,
                source_original_id=source_original_id,
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

    background_tasks.add_task(
        _background_ingest,
        job_id=job.id,
        workspace_id=req.workspace_id,
        file_data=None,
        content=req.content,
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

    router_ingest = IngestionRouter()
    try:
        mime_hint = file.content_type or ""
        parsed = router_ingest.route(data, filename=file.filename or "", mime_hint=mime_hint)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    content = parsed.raw_markdown

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

    background_tasks.add_task(
        _background_ingest,
        job_id=job.id,
        workspace_id=workspace_id,
        file_data=data,
        content=content,
        filename=file.filename,
        source_type=parsed.source_type,
        llm=llm,
        source_connector="upload",
        source_original_id=file.filename,
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

    background_tasks.add_task(
        _background_ingest,
        job_id=new_job.id,
        workspace_id=job.workspace_id,
        file_data=None,
        content=content or "retry",
        filename=job.filename,
        source_type=job.source_type,
        llm=llm,
    )

    return IngestJobCreateResponse(job_id=new_job.id, status=new_job.status.value)


async def _webhook_ingest(
    workspace_id: str,
    docs: list,
    connector_type: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
    llm,
):
    for parsed in docs:
        content = "\n\n".join(s.text for s in parsed.sections)
        filename = parsed.title + ".md"
        source_original_id = parsed.metadata.get("filepath") or parsed.metadata.get("source") or parsed.title

        job = IngestJob(
            id=new_uuid(),
            workspace_id=workspace_id,
            filename=filename,
            source_type=parsed.source_type,
            status=IngestJobStatus.pending,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        background_tasks.add_task(
            _background_ingest,
            job_id=job.id,
            workspace_id=workspace_id,
            file_data=None,
            content=content,
            filename=filename,
            source_type=parsed.source_type,
            llm=llm,
            source_connector=connector_type,
            source_original_id=source_original_id,
        )


@router.post("/webhook/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor"])),
    llm=Depends(get_llm_client),
):
    payload = await request.json()

    repo_full_name = payload.get("repository", {}).get("full_name", "")
    if not repo_full_name:
        raise HTTPException(status_code=400, detail="Missing repository full_name in payload")

    result = await db.execute(
        select(ConnectorConfig).where(
            ConnectorConfig.workspace_id == workspace_id,
            ConnectorConfig.connector_type == "git_webhook",
            ConnectorConfig.is_active == True,
        )
    )
    config_row = result.scalar_one_or_none()
    if not config_row:
        raise HTTPException(status_code=404, detail="No active git_webhook connector configured for this workspace")

    from app.ingestion.connectors.git_webhook import GitWebhookConnector
    connector = GitWebhookConnector()
    docs = await connector.process_push(config_row.config, payload)

    if not docs:
        return {"status": "ok", "ingested": 0, "message": "No new markdown files changed"}

    await _webhook_ingest(workspace_id, docs, "git_webhook", background_tasks, db, llm)
    return {"status": "ok", "ingested": len(docs)}


@router.post("/webhook/{source_key}")
async def generic_webhook(
    source_key: str,
    request: Request,
    background_tasks: BackgroundTasks,
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor"])),
    llm=Depends(get_llm_client),
):
    result = await db.execute(
        select(ConnectorConfig).where(
            ConnectorConfig.workspace_id == workspace_id,
            ConnectorConfig.connector_type == "generic_webhook",
            ConnectorConfig.is_active == True,
        )
    )
    config_row = result.scalar_one_or_none()
    if not config_row:
        raise HTTPException(status_code=404, detail="No active generic_webhook connector configured for this workspace")

    payload = await request.json()
    raw_bytes = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    from app.ingestion.connectors.generic_webhook import GenericWebhookConnector
    connector = GenericWebhookConnector()

    try:
        docs = await connector.process_payload(config_row.config, payload, raw_bytes, signature)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

    if not docs:
        return {"status": "ok", "ingested": 0}

    await _webhook_ingest(workspace_id, docs, "generic_webhook", background_tasks, db, llm)
    return {"status": "ok", "ingested": len(docs)}
