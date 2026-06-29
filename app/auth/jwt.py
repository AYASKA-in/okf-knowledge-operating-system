import time
import uuid
import jwt as pyjwt
from typing import Optional, Dict, Any

from app.config import settings


def create_access_token(user_id: str, workspace_id: str, role: str,
                        attributes: Optional[Dict[str, Any]] = None) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "ws": workspace_id,
        "role": role,
        "attrs": attributes or {},
        "iat": now,
        "exp": now + settings.jwt_expiry_hours * 3600,
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    now = int(time.time())
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + settings.jwt_refresh_expiry_days * 86400,
        "jti": str(uuid.uuid4()),
        "type": "refresh",
    }
    return pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return pyjwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError):
        return None
