"""
Authentication Routes
=====================
Handles user registration, login, and current user retrieval.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timezone, timedelta
import jwt
import uuid
from passlib.hash import bcrypt

from ..utils.database import get_db
from ..utils.auth import get_current_user
from ..config import JWT_SECRET, JWT_ALGORITHM

router = APIRouter()
security = HTTPBearer()


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str
    avatar_url: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
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

    class Config:
        extra = "ignore"


@router.post('/register', response_model=UserResponse)
async def register(user_data: UserCreate):
    """Register a new user"""
    db = get_db()
    
    existing = await db.users.find_one({'email': user_data.email}, {'_id': 0})
    if existing:
        raise HTTPException(status_code=400, detail='Email already registered')
    
    user_id = str(uuid.uuid4())
    hashed_password = bcrypt.hash(user_data.password)
    
    # Auto-approve supervisors and admins
    approved = user_data.role in ['supervisor', 'admin']
    
    user_doc = {
        'id': user_id,
        'email': user_data.email,
        'password_hash': hashed_password,
        'name': user_data.name,
        'role': user_data.role,
        'approved': approved,
        'avatar_url': user_data.avatar_url,
        'can_safeweb': False,
        'can_serpro': False,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    # Notify supervisors about pending approval
    if not approved:
        supervisors = await db.users.find({'role': 'supervisor'}, {'_id': 0}).to_list(100)
        for supervisor in supervisors:
            notif_doc = {
                'id': str(uuid.uuid4()),
                'user_id': supervisor['id'],
                'message': f'Novo usuário pendente de aprovação: {user_data.name} ({user_data.email})',
                'type': 'user_approval_pending',
                'read': False,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            await db.notifications.insert_one(notif_doc)
    
    return UserResponse(
        id=user_id,
        email=user_data.email,
        name=user_data.name,
        role=user_data.role,
        approved=approved,
        avatar_url=user_data.avatar_url,
        created_at=user_doc['created_at']
    )


@router.post('/login')
async def login(credentials: UserLogin):
    """Authenticate user and return JWT token"""
    db = get_db()
    
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"[LOGIN] Tentando login para: {credentials.email}")
    user = await db.users.find_one({'email': credentials.email}, {'_id': 0})
    logger.warning(f"[LOGIN] Usuário encontrado? {bool(user)}")
    if not user or not bcrypt.verify(credentials.password, user['password_hash']):
        logger.warning(f"[LOGIN] Credenciais inválidas para: {credentials.email}")
        raise HTTPException(status_code=401, detail='Invalid credentials')
    if not user.get('approved', False):
        logger.warning(f"[LOGIN] Conta não aprovada para: {credentials.email}")
        raise HTTPException(status_code=403, detail='Conta aguardando aprovação do supervisor')
    token_payload = {
        'user_id': user['id'],
        'exp': datetime.now(timezone.utc) + timedelta(days=7)
    }
    logger.warning(f"[LOGIN] Payload do token: {token_payload}")
    token = jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    logger.warning(f"[LOGIN] Token gerado: {token[:12]}... (mascarado)")
    return {
        'token': token,
        'user': UserResponse(**user)
    }


@router.get('/me', response_model=UserResponse)
async def get_me(current_user = Depends(get_current_user)):
    """Get current authenticated user"""
    return current_user
