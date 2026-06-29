from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.schemas import ChatRequest, ChatResponse
from app.models.db import Workspace, AuditLog, AuditAction
from app.agents.chat import ChatAgent
from app.storage.bundle import BundleManager
from app.config import settings
from app.auth.deps import require_role
from app.llm import get_llm_client

router = APIRouter(prefix="/v1/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_role(["admin", "editor", "viewer"])),
    llm=Depends(get_llm_client),
):
    result = await db.execute(select(Workspace).where(Workspace.id == req.workspace_id))
    workspace = result.scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    bundle = BundleManager(settings.okf_bundle_root, req.workspace_id)
    agent = ChatAgent(bundle, llm_client=llm)

    result_data = await agent.answer(req.message, req.conversation_id)

    audit = AuditLog(
        workspace_id=req.workspace_id,
        action=AuditAction.query,
        resource_type="chat",
        details={
            "conversation_id": result_data["conversation_id"],
            "question_length": len(req.message),
            "citation_count": len(result_data["citations"]),
        },
    )
    db.add(audit)

    return ChatResponse(
        answer=result_data["answer"],
        citations=result_data["citations"],
        conversation_id=result_data["conversation_id"],
    )
