import jwt
import os
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

# In production, this MUST be a strong, randomly generated string stored securely in .env
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-local-dev-key")
ALGORITHM = "HS256"

# A security scheme to extract the Bearer token from the Authorization header
security = HTTPBearer()

class TokenData(BaseModel):
    username: str
    roles: List[str]

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Creates a cryptographically signed JSON Web Token (JWT).
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Default expiration is 24 hours
        expire = datetime.utcnow() + timedelta(hours=24)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> TokenData:
    """
    Decodes the JWT and validates the cryptographic signature.
    If the signature is invalid or the token is expired, it raises an exception.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("username")
        roles: List[str] = payload.get("roles", [])
        
        if username is None:
            raise HTTPException(status_code=401, detail="Token missing username")
            
        return TokenData(username=username, roles=roles)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

def require_role(required_role: str):
    """
    A dependency you can inject into FastAPI routes to enforce Role-Based Access Control (RBAC).
    """
    def role_checker(credentials: HTTPAuthorizationCredentials = Security(security)):
        token_data = verify_token(credentials.credentials)
        if required_role not in token_data.roles:
            raise HTTPException(
                status_code=403, 
                detail=f"Forbidden: You do not have the required '{required_role}' role."
            )
        return token_data
    return role_checker
