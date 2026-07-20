import jwt
import os
import time
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-local-dev-key-32b!!")
ALGORITHM = "HS256"

security = HTTPBearer()


class TokenData(BaseModel):
    username: str
    role: str = "member"          # "admin" | "member"
    meeting_id: str = ""
    joined_at: float = 0.0        # Unix timestamp of when token was issued
    scope: str = "ingest:stream read:transcript"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Creates a cryptographically signed JWT.
    Bakes role, meeting_id, joined_at, and scope into the payload.
    """
    to_encode = data.copy()
    to_encode.setdefault("joined_at", time.time())
    to_encode.setdefault("scope", "ingest:stream read:transcript")
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=24))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> TokenData:
    """
    Decodes the JWT, validates the signature, and returns structured TokenData.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("username")
        if username is None:
            raise HTTPException(status_code=401, detail="Token missing username")

        return TokenData(
            username=username,
            role=payload.get("role", "member"),
            meeting_id=payload.get("meeting_id", ""),
            joined_at=float(payload.get("joined_at", 0.0)),
            scope=payload.get("scope", "ingest:stream read:transcript"),
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


def require_scope(required_scope: str):
    """
    FastAPI dependency: enforces that the JWT has a specific scope.
    Both admins and members have 'ingest:stream' and 'read:transcript'.
    """
    def checker(credentials: HTTPAuthorizationCredentials = Security(security)):
        token_data = verify_token(credentials.credentials)
        if required_scope not in token_data.scope:
            raise HTTPException(
                status_code=403,
                detail=f"Forbidden: Missing required scope '{required_scope}'."
            )
        return token_data
    return checker


def require_role(required_role: str):
    """
    FastAPI dependency: enforces that the JWT has a specific role.
    Only used for admin-only endpoints (e.g., toggle public).
    """
    def checker(credentials: HTTPAuthorizationCredentials = Security(security)):
        token_data = verify_token(credentials.credentials)
        if token_data.role != required_role:
            raise HTTPException(
                status_code=403,
                detail=f"Forbidden: Requires role '{required_role}'."
            )
        return token_data
    return checker
