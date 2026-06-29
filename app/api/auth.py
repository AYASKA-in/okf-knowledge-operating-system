from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.schemas import TokenRequest, TokenResponse, TokenRefreshRequest
from app.models.db import User
from app.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.auth.password import verify_password
from app.auth.deps import get_current_user

router = APIRouter(prefix="/v1/auth", tags=["Authentication"])


@router.post("/token", response_model=TokenResponse)
async def login(req: TokenRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    try:
        password_ok = verify_password(req.password, user.hashed_password)
    except Exception:
        password_ok = False

    if not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    access_token = create_access_token(
        user_id=user.id,
        workspace_id=user.workspace_id,
        role=user.role,
        attributes=user.attributes or {},
    )
    refresh_token = create_refresh_token(user_id=user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        workspace_id=user.workspace_id,
        role=user.role,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(req.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired or invalid",
        )
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Must be a refresh token.",
        )

    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )

    access_token = create_access_token(
        user_id=user.id,
        workspace_id=user.workspace_id,
        role=user.role,
        attributes=user.attributes or {},
    )
    new_refresh = create_refresh_token(user_id=user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        user_id=user.id,
        workspace_id=user.workspace_id,
        role=user.role,
    )


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user
