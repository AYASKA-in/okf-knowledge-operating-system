import tempfile
import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.schemas import ExportRequest
from app.models.db import Workspace, AuditLog, AuditAction
from app.storage.bundle import BundleManager
from app.storage.filesystem import FileSystemStore
from app.config import settings
from app.auth.deps import require_role

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


@router.post("")
async def export_bundle(
    req: ExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor"])),
):
    result = await db.execute(select(Workspace).where(Workspace.id == req.workspace_id))
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    bundle = BundleManager(settings.okf_bundle_root, req.workspace_id)
    tmp_dir = tempfile.mkdtemp(prefix="ekos_export_")
    cleanup_paths = [tmp_dir]

    try:
        export_path = bundle.export_bundle(tmp_dir)

        fs_store = FileSystemStore(settings.okf_bundle_root)
        zip_path = fs_store.create_zip_archive(export_path)
        cleanup_paths.append(zip_path)

        audit = AuditLog(
            workspace_id=req.workspace_id,
            action=AuditAction.export,
            resource_type="bundle",
            details={"format": req.format},
        )
        db.add(audit)

        background_tasks.add_task(cleanup_temp, cleanup_paths)

        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=f"{req.workspace_id}-okf-bundle.zip",
            headers={"Content-Disposition": f"attachment; filename={req.workspace_id}-okf-bundle.zip"},
        )
    except Exception as e:
        cleanup_temp(cleanup_paths)
        raise HTTPException(status_code=500, detail=f"Export failed: {e}")
