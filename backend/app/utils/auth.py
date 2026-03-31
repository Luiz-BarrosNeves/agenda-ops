"""
Authentication Utilities
========================
JWT token handling and user authentication.
"""

from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict
from typing import Optional
import jwt
import os

from .database import get_db

from ..config import JWT_SECRET, JWT_ALGORITHM

security = HTTPBearer()


class User(BaseModel):
    """User model for authentication"""
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    role: str
    approved: bool
    avatar_url: Optional[str] = None
    can_safeweb: bool = False
    can_serpro: bool = False
    is_online: Optional[bool] = False
    last_seen: Optional[str] = None
    created_at: str


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user from JWT token"""
    import logging
    logger = logging.getLogger("auth_attendants_debug")
    token = credentials.credentials
    # Identificador seguro do segredo
    secret_id = f"len={len(JWT_SECRET)}, head={JWT_SECRET[:2]}***tail={JWT_SECRET[-2:]}"
    logger.warning(f"[auth_attendants_debug] [TOKEN] Token recebido: {token[:10]}... (mascarado, len={len(token) if token else 0})")
    logger.warning(f"[auth_attendants_debug] [VALIDATION] JWT_ALGORITHM: {JWT_ALGORITHM}")
    logger.warning(f"[auth_attendants_debug] [VALIDATION] JWT_SECRET_ID: {secret_id}")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        logger.warning(f"[auth_attendants_debug] [PAYLOAD] Decodificado: {payload}")
        user_id = payload.get('user_id')
        logger.warning(f"[auth_attendants_debug] [USER_ID] Extraído: {user_id}")
        if not user_id:
            logger.warning(f"[auth_attendants_debug] [ERROR] user_id não encontrado no payload!")
            raise HTTPException(status_code=401, detail='Invalid token')
        db = get_db()
        user = await db.users.find_one({'id': user_id}, {'_id': 0})
        logger.warning(f"[auth_attendants_debug] [DB_LOOKUP] Resultado: {'encontrado' if user else 'não encontrado'} para user_id={user_id}")
        if user:
            logger.warning(f"[auth_attendants_debug] [USER_FOUND] id={user.get('id', 'N/A')}, role={user.get('role', 'N/A')}")
        if not user:
            logger.warning(f"[auth_attendants_debug] [ERROR] Usuário não encontrado no banco para id={user_id}")
            raise HTTPException(status_code=401, detail='User not found')
        return User(**user)
    except Exception as e:
        logger.exception(f"[auth_attendants_debug] [EXCEPTION] {type(e).__name__}: {str(e)}")
        if isinstance(e, jwt.ExpiredSignatureError):
            logger.warning(f"[auth_attendants_debug] [ERROR] Token expirado")
            raise HTTPException(status_code=401, detail='Token expired')
        if isinstance(e, jwt.InvalidTokenError):
            logger.warning(f"[auth_attendants_debug] [ERROR] Token inválido")
            raise HTTPException(status_code=401, detail='Invalid token')
        raise HTTPException(status_code=401, detail='Invalid token')


def require_role(*roles):
    """Dependency to require specific user roles"""
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=403, 
                detail=f'Access denied. Required roles: {", ".join(roles)}'
            )
        return current_user
    return role_checker
