import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.schemas import WorkspaceCreate, WorkspaceUpdate, UserCreate, UserUpdate
from app.models.db import Workspace, User
from app.config import settings
from app.auth.password import hash_password
from app.auth.deps import require_role

router = APIRouter(prefix="/v1/admin", tags=["Admin"])


@router.post("/workspaces", status_code=201)
async def create_workspace(
    req: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin"])),
):
    existing = await db.execute(select(Workspace).where(Workspace.name == req.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Workspace already exists")

    bucket = os.path.join(settings.okf_bundle_root, req.name).replace("\\", "/")

    ws = Workspace(name=req.name, description=req.description or "", bucket_path=bucket)
    db.add(ws)
    await db.flush()
    await db.refresh(ws)

    from app.storage.bundle import BundleManager
    BundleManager(settings.okf_bundle_root, ws.id)

    return {"id": ws.id, "name": ws.name, "bucket_path": bucket}


@router.get("/workspaces")
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin"])),
):
    result = await db.execute(select(Workspace).order_by(Workspace.created_at.desc()))
    workspaces = result.scalars().all()
    return [
        {
            "id": ws.id, "name": ws.name, "description": ws.description,
            "bucket_path": ws.bucket_path,
            "created_at": ws.created_at.isoformat(),
            "updated_at": ws.updated_at.isoformat(),
        }
        for ws in workspaces
    ]


@router.get("/workspaces/{workspace_id}")
async def get_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin"])),
):
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {
        "id": ws.id, "name": ws.name, "description": ws.description,
        "bucket_path": ws.bucket_path,
        "created_at": ws.created_at.isoformat(),
        "updated_at": ws.updated_at.isoformat(),
    }


@router.put("/workspaces/{workspace_id}")
async def update_workspace(
    workspace_id: str,
    req: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin"])),
):
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if req.name is not None:
        existing = await db.execute(
            select(Workspace).where(Workspace.name == req.name, Workspace.id != workspace_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Name already taken")
        ws.name = req.name
    if req.description is not None:
        ws.description = req.description

    return {
        "id": ws.id, "name": ws.name, "description": ws.description,
        "bucket_path": ws.bucket_path,
    }


@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin"])),
):
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ws = result.scalar_one_or_none()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    from app.storage.bundle import BundleManager
    bundle = BundleManager(settings.okf_bundle_root, workspace_id)
    if bundle.workspace_path.exists():
        shutil.rmtree(bundle.workspace_path, ignore_errors=True)

    await db.delete(ws)
    return {"status": "ok", "deleted": workspace_id}


@router.post("/users", status_code=201)
async def create_user(
    req: UserCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin"])),
):
    ws_result = await db.execute(select(Workspace).where(Workspace.id == req.workspace_id))
    if not ws_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Workspace not found")

    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="User already exists")

    hashed = hash_password(req.password)

    user = User(
        workspace_id=req.workspace_id,
        email=req.email,
        hashed_password=hashed,
        display_name=req.display_name,
        role=req.role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    return {"id": user.id, "email": user.email, "role": user.role,
            "workspace_id": user.workspace_id}


@router.get("/users")
async def list_users(
    workspace_id: str = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin"])),
):
    query = select(User).order_by(User.created_at.desc())
    if workspace_id:
        query = query.where(User.workspace_id == workspace_id)
    result = await db.execute(query)
    users = result.scalars().all()
    return [
        {
            "id": u.id, "workspace_id": u.workspace_id,
            "email": u.email, "display_name": u.display_name,
            "role": u.role, "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
            "updated_at": u.updated_at.isoformat(),
        }
        for u in users
    ]


@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin"])),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id, "workspace_id": user.workspace_id,
        "email": user.email, "display_name": user.display_name,
        "role": user.role, "is_active": user.is_active,
        "created_at": user.created_at.isoformat(),
        "updated_at": user.updated_at.isoformat(),
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    req: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin"])),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if req.email is not None:
        existing = await db.execute(
            select(User).where(User.email == req.email, User.id != user_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already taken")
        user.email = req.email
    if req.display_name is not None:
        user.display_name = req.display_name
    if req.role is not None:
        user.role = req.role
    if req.is_active is not None:
        user.is_active = req.is_active

    return {
        "id": user.id, "workspace_id": user.workspace_id,
        "email": user.email, "display_name": user.display_name,
        "role": user.role, "is_active": user.is_active,
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin"])),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    return {"status": "ok", "deleted": user_id}


@router.get("/audit-logs")
async def get_audit_logs(
    workspace_id: str = Query(None),
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin"])),
):
    from app.models.db import AuditLog
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(100)
    if workspace_id:
        query = query.where(AuditLog.workspace_id == workspace_id)
    result = await db.execute(query)
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "action": log.action.value,
            "resource_type": log.resource_type,
            "details": log.details,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]
