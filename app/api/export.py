import os
import tempfile
import shutil
import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.database import get_db, get_session_factory
from app.models.schemas import ExportRequest, ExportCreateResponse, ExportJobResponse
from app.models.db import (
    Workspace, ExportJob, ExportJobStatus,
    AuditLog, AuditAction, new_uuid,
)
from app.storage.bundle import BundleManager
from app.storage.filesystem import FileSystemStore
from app.config import settings
from app.auth.deps import require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/export", tags=["Export"])


def cleanup_temp(paths: list[str]):
    for p in paths:
        try:
            if os.path.isfile(p):
                os.unlink(p)
            elif os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)
        except Exception:
            pass


async def _background_export(
    workspace_id: str,
    job_id: str,
    fmt: str,
):
    factory = get_session_factory()
    async with factory() as db:
        try:
            bundle = BundleManager(settings.okf_bundle_root, workspace_id)
            tmp_dir = tempfile.mkdtemp(prefix=f"ekos_export_{job_id[:8]}_")
            cleanup_paths = [tmp_dir]

            job_result = await db.execute(select(ExportJob).where(ExportJob.id == job_id))
            job = job_result.scalar_one_or_none()
            if not job:
                return

            job.status = ExportJobStatus.running
            await db.commit()

            export_path = bundle.export_bundle(tmp_dir)
            fs_store = FileSystemStore(settings.okf_bundle_root)
            zip_path = fs_store.create_zip_archive(export_path)
            cleanup_paths.append(zip_path)

            file_size = os.path.getsize(zip_path)

            export_storage = os.path.join(settings.okf_bundle_root, "exports")
            os.makedirs(export_storage, exist_ok=True)
            final_path = os.path.join(export_storage, f"{job_id}.zip")
            shutil.copy2(zip_path, final_path)

            job.status = ExportJobStatus.done
            job.filename = f"{workspace_id}-okf-bundle.zip"
            job.file_size = file_size
            job.file_path = final_path
            job.completed_at = datetime.now(timezone.utc)
            await db.commit()

            audit = AuditLog(
                id=new_uuid(),
                workspace_id=workspace_id,
                action=AuditAction.export,
                resource_type="bundle",
                details={"job_id": job_id, "format": fmt, "file_size": file_size},
            )
            db.add(audit)
            await db.commit()
        except Exception as e:
            try:
                job_result = await db.execute(select(ExportJob).where(ExportJob.id == job_id))
                job = job_result.scalar_one_or_none()
                if job:
                    job.status = ExportJobStatus.failed
                    job.error_message = str(e)[:2000]
                    job.completed_at = datetime.now(timezone.utc)
                    await db.commit()
            except Exception:
                pass
            logger.error("Export job %s failed: %s", job_id, e)
        finally:
            cleanup_temp(cleanup_paths)


@router.post("", response_model=ExportCreateResponse, status_code=202)
async def create_export(
    req: ExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor"])),
):
    result = await db.execute(select(Workspace).where(Workspace.id == req.workspace_id))
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    job = ExportJob(
        id=new_uuid(),
        workspace_id=req.workspace_id,
        status=ExportJobStatus.pending,
        format=req.format or "zip",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    background_tasks.add_task(
        _background_export,
        workspace_id=req.workspace_id,
        job_id=job.id,
        fmt=req.format,
    )

    return ExportCreateResponse(job_id=job.id, status=job.status.value)


@router.get("/jobs", response_model=List[ExportJobResponse])
async def list_export_jobs(
    workspace_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor"])),
):
    result = await db.execute(
        select(ExportJob)
        .where(ExportJob.workspace_id == workspace_id)
        .order_by(ExportJob.created_at.desc())
    )
    rows = result.scalars().all()
    return [
        ExportJobResponse(
            id=r.id, workspace_id=r.workspace_id, status=r.status.value,
            format=r.format, filename=r.filename, file_size=r.file_size,
            error_message=r.error_message, created_at=r.created_at,
            updated_at=r.updated_at, completed_at=r.completed_at,
        )
        for r in rows
    ]


@router.get("/jobs/{job_id}", response_model=ExportJobResponse)
async def get_export_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor"])),
):
    result = await db.execute(select(ExportJob).where(ExportJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    return ExportJobResponse(
        id=job.id, workspace_id=job.workspace_id, status=job.status.value,
        format=job.format, filename=job.filename, file_size=job.file_size,
        error_message=job.error_message, created_at=job.created_at,
        updated_at=job.updated_at, completed_at=job.completed_at,
    )


@router.get("/jobs/{job_id}/download")
async def download_export(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor"])),
):
    result = await db.execute(select(ExportJob).where(ExportJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")
    if job.status != ExportJobStatus.done:
        raise HTTPException(
            status_code=400,
            detail=f"Export not ready (status: {job.status.value})",
        )
    if not job.file_path or not os.path.isfile(job.file_path):
        raise HTTPException(status_code=404, detail="Export file not found on disk")

    return FileResponse(
        job.file_path,
        media_type="application/zip",
        filename=job.filename or f"{job.workspace_id}-okf-bundle.zip",
    )
