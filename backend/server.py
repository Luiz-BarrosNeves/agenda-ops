from app.utils.auth import get_current_user as centralized_get_current_user
print("SERVER LOADED FROM:", __file__)
def check_role_permission(current_user, allowed_roles, action='realizar esta ação'):
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail=f'Usuário do perfil {current_user.role} não pode {action}')

def block_admin(current_user):
    if current_user.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail='Usuário ADMIN não pode realizar esta ação')

def block_agent(current_user):
    if current_user.role == UserRole.AGENTE:
        raise HTTPException(status_code=403, detail='Usuário AGENTE não pode realizar esta ação')

def validate_agent_update_fields(update_data, apt, current_user):
    # AGENTE só pode alterar date e time_slot do próprio agendamento
    allowed_fields = {'date', 'time_slot'}
    for field in update_data:
        if field not in allowed_fields:
            raise HTTPException(status_code=403, detail='AGENTE só pode alterar data e horário do próprio agendamento')
    if apt.get('user_id') != current_user.id:
        raise HTTPException(status_code=403, detail='AGENTE só pode editar o próprio agendamento')

def validate_no_agent_assignment(update_data, current_user):
    # Comercial/Televendas não podem alterar campos de agente
    agent_fields = {'user_id', 'user_name', 'new_agent_id', 'new_agent_name', 'available_agent'}
    for field in update_data:
        if field in agent_fields:
            raise HTTPException(status_code=403, detail='Você não tem permissão para designar ou alterar agente')
"""
AgendaHub Backend Server
========================

Este arquivo é o ponto de entrada principal do backend.
A estrutura modular está em /app/backend/app/ para organização.

Para detalhes da arquitetura, veja: /app/backend/ARCHITECTURE.md

Módulos disponíveis:
- app/config.py: Configurações centralizadas
- app/models/: Modelos Pydantic
- app/services/: Lógica de negócio
- app/utils/: Utilitários (auth, database)
"""

from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Query
from app.routes.users import router as users_router
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import shutil
import asyncio
import csv
import io
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from zoneinfo import ZoneInfo
BR_TZ = ZoneInfo("America/Sao_Paulo")
from zoneinfo import ZoneInfo
BR_TZ = ZoneInfo("America/Sao_Paulo")
import jwt
from passlib.hash import bcrypt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

UPLOAD_DIR = ROOT_DIR / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Criação do app FastAPI
# Criação do app FastAPI
app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

origins = [
    "http://localhost:3000",
    "https://agenda-ops.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# CORS para frontend local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# CORS para frontend local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
api_router = APIRouter(prefix="/api")
api_router.include_router(users_router, prefix="/users")
security = HTTPBearer()

from app.config import JWT_SECRET, JWT_ALGORITHM
AUTO_ASSIGN_MINUTES = 5  # Tempo para atribuição automática
PRESENCE_TIMEOUT_MINUTES = 3  # Tempo sem heartbeat para considerar offline
auto_assign_task = None  # Referência para a task de background
presence_check_task = None  # Referência para a task de verificação de presença

class UserRole:
    ADMIN = 'admin'
    SUPERVISOR = 'supervisor'
    AGENTE = 'agente'
    TELEVENDAS = 'televendas'
    COMERCIAL = 'comercial'

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str
    avatar_url: Optional[str] = None
    approved: bool = False
    can_safeweb: bool = False
    can_serpro: bool = False

class UserApprove(BaseModel):
    approved: bool

class UserUpdateRole(BaseModel):
    role: str

class UserUpdatePermissions(BaseModel):
    can_safeweb: Optional[bool] = None
    can_serpro: Optional[bool] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
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

class AppointmentCreate(BaseModel):
    first_name: str
    last_name: str
    protocol_number: str
    additional_protocols: Optional[List[str]] = []
    has_chat: bool = False
    chat_platform: Optional[str] = None  # 'blip' ou 'chatpro' (obrigatório se has_chat=True)
    date: str
    time_slot: str
    notes: Optional[str] = None
    emission_system: Optional[str] = None  # 'safeweb', 'serpro', ou None
    reschedule_reason: Optional[str] = None  # Motivo do reagendamento (padronizado)

class AppointmentAssign(BaseModel):
    user_id: str

class AppointmentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    protocol_number: Optional[str] = None
    additional_protocols: Optional[List[str]] = None
    has_chat: Optional[bool] = None
    chat_platform: Optional[str] = None  # 'blip' ou 'chatpro'
    date: Optional[str] = None
    time_slot: Optional[str] = None
    appointment_type: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    emission_system: Optional[str] = None
    reschedule_reason: Optional[str] = None  # Motivo do reagendamento (padronizado)

class Appointment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: Optional[str] = None
    first_name: str
    last_name: str
    protocol_number: str
    additional_protocols: List[str] = []
    has_chat: bool
    chat_platform: Optional[str] = None  # 'blip' ou 'chatpro'
    document_urls: List[str] = []
    date: str
    time_slot: str
    appointment_type: str
    status: str
    notes: Optional[str] = None
    emission_system: Optional[str] = None  # 'safeweb', 'serpro', ou None
    created_by: str
    created_at: str
    updated_at: str
    reserved_at: str
    reschedule_reason: Optional[str] = None  # Motivo do reagendamento (padronizado)

class NotificationCreate(BaseModel):
    user_id: str
    message: str
    type: str

class Notification(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    message: str
    type: str
    read: bool
    created_at: str

# ============== HISTORY/AUDIT MODELS ==============

class AppointmentHistory(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    appointment_id: str
    action: str  # created, updated, status_changed, assigned, rescheduled
    field_changed: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by: str
    changed_by_name: str
    changed_at: str

# ============== RECURRING APPOINTMENT MODELS ==============

class RecurringAppointmentCreate(BaseModel):
    first_name: str
    last_name: str
    base_protocol: str  # Protocolo base para referência
    new_protocol: str   # Novo protocolo para este reagendamento
    additional_protocols: Optional[List[str]] = []
    has_chat: bool = False
    chat_platform: Optional[str] = None  # 'blip' ou 'chatpro'
    date: str
    time_slot: str
    notes: Optional[str] = None
    original_appointment_id: Optional[str] = None  # Referência ao agendamento original

# ============== APPOINTMENT TEMPLATES ==============

class AppointmentTemplateCreate(BaseModel):
    name: str  # Nome do template (ex: "João Silva - Semanal")
    client_first_name: str
    client_last_name: str
    preferred_time_slot: Optional[str] = None  # Horário preferido
    preferred_day_of_week: Optional[int] = None  # 0=Segunda, 6=Domingo
    has_chat: bool = False
    chat_platform: Optional[str] = None  # 'blip' ou 'chatpro'
    notes: Optional[str] = None
    tags: Optional[List[str]] = []  # Tags para organização (ex: "VIP", "Urgente")

class AppointmentTemplateUpdate(BaseModel):
    name: Optional[str] = None
    client_first_name: Optional[str] = None
    client_last_name: Optional[str] = None
    preferred_time_slot: Optional[str] = None
    preferred_day_of_week: Optional[int] = None
    has_chat: Optional[bool] = None
    chat_platform: Optional[str] = None  # 'blip' ou 'chatpro'
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

class AppointmentTemplate(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    client_first_name: str
    client_last_name: str
    preferred_time_slot: Optional[str] = None
    preferred_day_of_week: Optional[int] = None
    has_chat: bool = False
    chat_platform: Optional[str] = None  # 'blip' ou 'chatpro'
    notes: Optional[str] = None
    tags: List[str] = []
    created_by: str
    created_at: str
    updated_at: str
    use_count: int = 0  # Contador de vezes que foi usado
    last_used_at: Optional[str] = None

# ============== SOLICITAÇÕES DE EDIÇÃO/CANCELAMENTO ==============

class ChangeRequestType:
    EDIT = 'edit'
    CANCEL = 'cancel'

class ChangeRequestStatus:
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    AUTO_APPROVED = 'auto_approved'  # Aprovado automaticamente por proximidade do horário

class ChangeRequestCreate(BaseModel):
    appointment_id: str
    request_type: str  # 'edit' ou 'cancel'
    reason: Optional[str] = None
    # Campos para edição (opcional)
    new_first_name: Optional[str] = None
    new_last_name: Optional[str] = None
    new_protocol_number: Optional[str] = None
    new_additional_protocols: Optional[List[str]] = None
    new_date: Optional[str] = None
    new_time_slot: Optional[str] = None
    new_notes: Optional[str] = None

class ChangeRequestResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    appointment_id: str
    request_type: str
    status: str
    reason: Optional[str] = None
    new_first_name: Optional[str] = None
    new_last_name: Optional[str] = None
    new_protocol_number: Optional[str] = None
    new_additional_protocols: Optional[List[str]] = None
    new_date: Optional[str] = None
    new_time_slot: Optional[str] = None
    new_notes: Optional[str] = None
    requested_by: str
    requested_by_name: str
    created_at: str
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    review_notes: Optional[str] = None

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"[get_current_user] credentials recebido? {credentials is not None}")
    token = credentials.credentials if credentials else None
    logger.warning(f"[get_current_user] token recebido? {token is not None}")
    logger.warning(f"[get_current_user] tamanho do token: {len(token) if token else 0}")
    if token:
        logger.warning(f"[get_current_user] prefixo token: {token[:10]}... (mascarado)")
    else:
        logger.warning("[get_current_user] token ausente")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get('user_id')
        if not user_id:
            raise HTTPException(status_code=401, detail='Invalid token')
        user = await db.users.find_one({'id': user_id}, {'_id': 0})
        if not user:
            raise HTTPException(status_code=401, detail='User not found')
        return User(**user)
    except Exception as e:
        logger.exception(f"[get_current_user] Exceção: {type(e).__name__} - {str(e)}")
        if isinstance(e, jwt.ExpiredSignatureError):
            raise HTTPException(status_code=401, detail='Token expired')
        if isinstance(e, jwt.InvalidTokenError):
            raise HTTPException(status_code=401, detail='Invalid token')
        raise HTTPException(status_code=401, detail='Invalid token')

@api_router.post('/auth/register', response_model=User)
async def register(user_data: UserCreate):
    existing = await db.users.find_one({'email': user_data.email}, {'_id': 0})
    if existing:
        raise HTTPException(status_code=400, detail='Email already registered')
    
    user_id = str(uuid.uuid4())
    hashed_password = bcrypt.hash(user_data.password)
    
    approved = user_data.role == 'supervisor' or user_data.role == 'admin'
    
    user_doc = {
        'id': user_id,
        'email': user_data.email,
        'password_hash': hashed_password,
        'name': user_data.name,
        'role': user_data.role,
        'approved': approved,
        'avatar_url': user_data.avatar_url,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    
    if not approved:
        supervisors = await db.users.find({'role': {'$in': ['supervisor']}}, {'_id': 0}).to_list(100)
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
    
    return User(id=user_id, email=user_data.email, name=user_data.name, 
                role=user_data.role, approved=approved, avatar_url=user_data.avatar_url, 
                created_at=user_doc['created_at'])

@api_router.post('/auth/login')
async def login(credentials: UserLogin):
    user = await db.users.find_one({'email': credentials.email}, {'_id': 0})
    if not user or not bcrypt.verify(credentials.password, user['password_hash']):
        raise HTTPException(status_code=401, detail='Invalid credentials')
    
    if not user.get('approved', False):
        raise HTTPException(status_code=403, detail='Conta aguardando aprovação do supervisor')
    
    import logging
    logger = logging.getLogger("jwt_login_debug")
    payload = {
        'user_id': user['id'],
        'exp': datetime.now(timezone.utc) + timedelta(days=7)
    }
    # Identificador seguro do segredo
    secret_id = f"len={len(JWT_SECRET)}, head={JWT_SECRET[:2]}***tail={JWT_SECRET[-2:]}"
    logger.warning(f"[jwt_login_debug] [GENERATION] Função: login (server.py)")
    logger.warning(f"[jwt_login_debug] [GENERATION] JWT_ALGORITHM: {JWT_ALGORITHM}")
    logger.warning(f"[jwt_login_debug] [GENERATION] JWT_SECRET_ID: {secret_id}")
    logger.warning(f"[jwt_login_debug] [GENERATION] Payload: {payload}")
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {
        'token': token,
        'user': User(**user)
    }

@api_router.get('/auth/me', response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@api_router.get('/users', response_model=List[User])
async def get_users(
    pending_approval: Optional[bool] = None,
    current_user: User = Depends(get_current_user)
):
    # Admin pode visualizar usuários, mas não pode fazer alterações
    if current_user.role not in ['supervisor', 'admin']:
        raise HTTPException(status_code=403, detail='Acesso não autorizado')
    
    query = {}
    if pending_approval is not None:
        query['approved'] = not pending_approval
    
    users = await db.users.find(query, {'_id': 0, 'password_hash': 0}).to_list(100)
    return [User(**u) for u in users]

@api_router.put('/users/{user_id}/approve')
async def approve_user(user_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != 'supervisor':
        raise HTTPException(status_code=403, detail='Only supervisors can approve users')
    
    result = await db.users.update_one(
        {'id': user_id},
        {'$set': {'approved': True}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail='User not found')
    
    return {'message': 'User approved successfully'}

@api_router.put('/users/{user_id}/role')
async def update_user_role(
    user_id: str, 
    role_data: UserUpdateRole,
    current_user: User = Depends(get_current_user)
):
    if current_user.role != 'supervisor':
        raise HTTPException(status_code=403, detail='Only supervisors can change user roles')
    
    result = await db.users.update_one(
        {'id': user_id},
        {'$set': {'role': role_data.role}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail='User not found')
    
    return {'message': 'User role updated successfully'}

@api_router.put('/users/{user_id}/permissions')
async def update_user_permissions(
    user_id: str, 
    perm_data: UserUpdatePermissions,
    current_user: User = Depends(get_current_user)
):
    """Atualizar permissões de Safeweb/Serpro do usuário"""
    if current_user.role != 'supervisor':
        raise HTTPException(status_code=403, detail='Apenas supervisores podem alterar permissões')
    
    update_data = {}
    if perm_data.can_safeweb is not None:
        update_data['can_safeweb'] = perm_data.can_safeweb
    if perm_data.can_serpro is not None:
        update_data['can_serpro'] = perm_data.can_serpro
    
    if not update_data:
        raise HTTPException(status_code=400, detail='Nenhuma permissão para atualizar')
    
    result = await db.users.update_one(
        {'id': user_id},
        {'$set': update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail='Usuário não encontrado')
    
    return {'message': 'Permissões atualizadas com sucesso'}

@api_router.get('/users/with-permission/{system}')
async def get_users_with_permission(
    system: str,
    current_user: User = Depends(get_current_user)
):
    """Obter lista de usuários com permissão para um sistema específico"""
    if system not in ['safeweb', 'serpro']:
        raise HTTPException(status_code=400, detail='Sistema deve ser safeweb ou serpro')
    
    field = f'can_{system}'
    users = await db.users.find({
        field: True,
        'role': UserRole.AGENTE,
        'approved': True
    }, {'_id': 0, 'password_hash': 0}).to_list(100)
    
    return [User(**u) for u in users]

@api_router.delete('/users/{user_id}')
async def delete_user(user_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != 'supervisor':
        raise HTTPException(status_code=403, detail='Only supervisors can delete users')
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail='Cannot delete yourself')
    
    result = await db.users.delete_one({'id': user_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail='User not found')
    
    return {'message': 'User deleted successfully'}

@api_router.get('/users/attendants', response_model=List[User])
async def get_attendants(current_user: 'User' = Depends(centralized_get_current_user)):
    import logging
    logger = logging.getLogger("attendants_route")
    logger.warning("[attendants_route] [ENTRY] Entrou no handler /users/attendants (server.py)")
    try:
        logger.warning(f"[attendants_route] [USER] current_user: {repr(current_user)}")
        logger.warning(f"[attendants_route] [ROLE] user_id={getattr(current_user, 'id', None)}, role={getattr(current_user, 'role', None)}")
        if current_user.role != UserRole.SUPERVISOR:
            logger.warning(f"[attendants_route] [FORBIDDEN] Acesso negado para usuário id={getattr(current_user, 'id', None)}, role={getattr(current_user, 'role', None)}")
            raise HTTPException(status_code=403, detail='Not authorized')
        users = await db.users.find({
            'role': {'$in': [UserRole.AGENTE]},
            'approved': True
        }, {'_id': 0, 'password_hash': 0}).to_list(100)
        logger.warning(f"[attendants_route] [SUCCESS] Retornando {len(users)} agentes para supervisor id={getattr(current_user, 'id', None)}")
        return [User(**u) for u in users]
    except Exception as e:
        logger.exception(f"[attendants_route] [EXCEPTION] {type(e).__name__}: {str(e)}")
        raise

@api_router.get('/users/stats/team')
async def get_team_stats(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERVISOR]:
        raise HTTPException(status_code=403, detail='Not authorized')
    
    users = await db.users.find({
        'role': UserRole.AGENTE,
        'approved': True
    }, {'_id': 0}).to_list(100)
    
    stats = []
    today = datetime.now(timezone.utc).date().isoformat()
    
    for user in users:
        appointments = await db.appointments.find({
            'user_id': user['id'],
            'date': today,
            'status': {'$ne': 'cancelado'}
        }, {'_id': 0}).to_list(1000)
        
        total_sessions = len(appointments)
        
        stats.append({
            'user_id': user['id'],
            'name': user['name'],
            'avatar_url': user.get('avatar_url'),
            'total_appointments': total_sessions,
            'total_sessions': total_sessions,
            'status': 'overloaded' if total_sessions > 15 else 'available' if total_sessions < 8 else 'normal'
        })
    
    return stats

@api_router.post('/appointments', response_model=Appointment)
async def create_appointment(apt_data: AppointmentCreate, current_user: User = Depends(get_current_user)):
    block_admin(current_user)
    block_agent(current_user)
    check_role_permission(current_user, [UserRole.TELEVENDAS, UserRole.COMERCIAL, UserRole.SUPERVISOR], 'criar agendamentos')
    
    apt_date = datetime.fromisoformat(apt_data.date)
    now = datetime.now(timezone.utc)
    today = now.date()
    
    if apt_date.date() < today:
        raise HTTPException(status_code=400, detail='Não é permitido agendar para dia anterior')
    

    # Interpreta o horário como America/Sao_Paulo (timezone-aware)
    BR_TZ = ZoneInfo("America/Sao_Paulo")
    apt_local = datetime.fromisoformat(f"{apt_data.date}T{apt_data.time_slot}:00").replace(tzinfo=BR_TZ)
    apt_utc = apt_local.astimezone(timezone.utc)

    if apt_utc <= now:
        raise HTTPException(status_code=400, detail='Não é permitido agendar para horário que já passou')
    
    # Validar permissões se emission_system for especificado
    emission_system = apt_data.emission_system
    if emission_system and emission_system not in ['safeweb', 'serpro']:
        raise HTTPException(status_code=400, detail='Sistema de emissão inválido')
    
    # Verificar se há agentes com permissão para o sistema especificado
    if emission_system:
        perm_field = f'can_{emission_system}'
        agents_with_permission = await db.users.count_documents({
            perm_field: True,
            'role': UserRole.AGENTE,
            'approved': True
        })
        if agents_with_permission == 0:
            raise HTTPException(
                status_code=400, 
                detail=f'Não há agentes com permissão para {emission_system.upper()}'
            )
    
    # Validar chat_platform se has_chat for True
    if apt_data.has_chat:
        if not apt_data.chat_platform or apt_data.chat_platform not in ['blip', 'chatpro']:
            raise HTTPException(
                status_code=400, 
                detail='Quando o cliente tem chat, é obrigatório selecionar a plataforma (Blip ou Chatpro)'
            )
    
    total_protocols = 1 + len(apt_data.additional_protocols)
    slots_needed = 2 if total_protocols >= 3 else 1
    
    apt_id = str(uuid.uuid4())
    now_str = now.isoformat()
    
    apt_doc = {
        'id': apt_id,
        'user_id': None,
        'first_name': apt_data.first_name,
        'last_name': apt_data.last_name,
        'protocol_number': apt_data.protocol_number,
        'additional_protocols': apt_data.additional_protocols,
        'has_chat': apt_data.has_chat,
        'chat_platform': apt_data.chat_platform if apt_data.has_chat else None,
        'document_urls': [],
        'date': apt_data.date,
        'time_slot': apt_data.time_slot,
        'appointment_type': 'videoconferencia',
        'status': 'pendente_atribuicao',
        'notes': apt_data.notes,
        'emission_system': emission_system,
        'created_by': current_user.id,
        'created_at': now_str,
        'updated_at': now_str,
        'reserved_at': now_str,
        'slots_needed': slots_needed
    }
    
    await db.appointments.insert_one(apt_doc)
    
    # Registrar histórico de criação
    await log_appointment_history(
        apt_id,
        'created',
        current_user.id,
        current_user.name
    )
    
    if slots_needed == 2:
        # Corrigir: apt_datetime não definido, usar apt_local
        next_slot_time = (apt_local + timedelta(minutes=20)).strftime('%H:%M')
        apt_id_2 = str(uuid.uuid4())
        apt_doc_2 = {
            'id': apt_id_2,
            'user_id': None,
            'first_name': apt_data.first_name,
            'last_name': apt_data.last_name,
            'protocol_number': apt_data.protocol_number,
            'additional_protocols': apt_data.additional_protocols,
            'has_chat': apt_data.has_chat,
            'chat_platform': apt_data.chat_platform if apt_data.has_chat else None,
            'document_urls': [],
            'date': apt_data.date,
            'time_slot': next_slot_time,
            'appointment_type': 'videoconferencia',
            'status': 'pendente_atribuicao',
            'notes': f'{apt_data.notes} - PARTE 2/2',
            'emission_system': emission_system,
            'created_by': current_user.id,
            'created_at': now_str,
            'updated_at': now_str,
            'reserved_at': now_str,
            'slots_needed': 2,
            'linked_appointment': apt_id
        }
        await db.appointments.insert_one(apt_doc_2)
        await db.appointments.update_one({'id': apt_id}, {'$set': {'linked_appointment': apt_id_2}})
    
    # Mensagem de notificação especial para agendamentos Safeweb/Serpro
    notification_msg = f'Novo agendamento pendente: {apt_data.first_name} {apt_data.last_name}'
    if emission_system:
        notification_msg = f'[{emission_system.upper()}] {notification_msg}'
    
    supervisors = await db.users.find({
        'role': {'$in': [UserRole.SUPERVISOR]}
    }, {'_id': 0}).to_list(100)
    
    for supervisor in supervisors:
        notif_doc = {
            'id': str(uuid.uuid4()),
            'user_id': supervisor['id'],
            'appointment_id': apt_id,
            'message': notification_msg,
            'type': 'pending_assignment',
            'read': False,
            'created_at': now_str
        }
        await db.notifications.insert_one(notif_doc)
    
    return Appointment(**apt_doc)

@api_router.put('/appointments/{apt_id}/assign', response_model=Appointment)
async def assign_appointment(
    apt_id: str,
    assign_data: AppointmentAssign,
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail='Apenas supervisores podem atribuir agendamentos')
    
    apt = await db.appointments.find_one({'id': apt_id}, {'_id': 0})
    if not apt:
        raise HTTPException(status_code=404, detail='Appointment not found')
    
    # Buscar dados do agente
    agent = await db.users.find_one({'id': assign_data.user_id}, {'_id': 0})
    if not agent:
        raise HTTPException(status_code=404, detail='Agente não encontrado')
    
    # Verificar permissões de Safeweb/Serpro
    emission_system = apt.get('emission_system')
    if emission_system:
        perm_field = f'can_{emission_system}'
        if not agent.get(perm_field, False):
            raise HTTPException(
                status_code=400, 
                detail=f'Este agente não tem permissão para atendimentos {emission_system.upper()}. Selecione um agente com essa permissão.'
            )
    
    existing = await db.appointments.find_one({
        'user_id': assign_data.user_id,
        'date': apt['date'],
        'time_slot': apt['time_slot'],
        'status': {'$ne': 'cancelado'}
    }, {'_id': 0})
    
    if existing:
        raise HTTPException(status_code=400, detail='Agente já possui agendamento neste horário')
    
    update_data = {
        'user_id': assign_data.user_id,
        'status': 'confirmado',
        'updated_at': datetime.now(timezone.utc).isoformat()
    }
    
    await db.appointments.update_one({'id': apt_id}, {'$set': update_data})
    
    # Buscar nome do agente para o histórico
    agent = await db.users.find_one({'id': assign_data.user_id}, {'_id': 0})
    agent_name = agent['name'] if agent else 'Desconhecido'
    
    # Registrar histórico de atribuição
    await log_appointment_history(
        apt_id,
        'assigned',
        current_user.id,
        current_user.name,
        field_changed='user_id',
        old_value=None,
        new_value=agent_name
    )
    
    await db.notifications.delete_many({
        'appointment_id': apt_id,
        'type': 'pending_assignment'
    })
    
    notif_doc = {
        'id': str(uuid.uuid4()),
        'user_id': assign_data.user_id,
        'message': f'Novo agendamento atribuído: {apt["first_name"]} {apt["last_name"]}',
        'type': 'appointment_assigned',
        'read': False,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notif_doc)
    
    updated_apt = await db.appointments.find_one({'id': apt_id}, {'_id': 0})
    return Appointment(**updated_apt)

@api_router.get('/appointments', response_model=List[Appointment])
async def get_appointments(
    date: Optional[str] = None,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {}
    
    if current_user.role == UserRole.AGENTE:
        query['user_id'] = current_user.id
    
    if date:
        query['date'] = date
    if status:
        query['status'] = status
    if user_id and current_user.role in [UserRole.ADMIN, UserRole.SUPERVISOR]:
        query['user_id'] = user_id
    
    appointments = await db.appointments.find(query, {'_id': 0}).sort('time_slot', 1).to_list(1000)
    # Preencher agent_name para todos os agendamentos
    for apt in appointments:
        if apt.get('user_id'):
            agent = await db.users.find_one({'id': apt['user_id']}, {'_id': 0, 'name': 1})
            apt['agent_name'] = agent.get('name') if agent else 'Desconhecido'
        else:
            apt['agent_name'] = None
    return [Appointment(**apt) for apt in appointments]

# ============== REDISTRIBUIÇÃO INTELIGENTE ==============

class RedistributionRequest(BaseModel):
    target_appointment_id: str  # Agendamento especial (safeweb/serpro) que precisa de atribuição

class RedistributionResult(BaseModel):
    success: bool
    message: str
    moved_appointment_id: Optional[str] = None
    freed_agent_id: Optional[str] = None
    freed_agent_name: Optional[str] = None
    new_agent_id: Optional[str] = None
    new_agent_name: Optional[str] = None

@api_router.post('/appointments/redistribute')
async def redistribute_for_special_appointment(
    request: RedistributionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Redistribui agendamentos para liberar um agente com permissão especial.
    Usado quando um novo agendamento Safeweb/Serpro precisa de um agente com permissão,
    mas todos os agentes com permissão estão ocupados com agendamentos comuns.
    """
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail='Apenas supervisores podem redistribuir')
    
    # Buscar o agendamento especial que precisa de atribuição
    target_apt = await db.appointments.find_one({'id': request.target_appointment_id}, {'_id': 0})
    if not target_apt:
        raise HTTPException(status_code=404, detail='Agendamento não encontrado')
    
    emission_system = target_apt.get('emission_system')
    if not emission_system:
        raise HTTPException(status_code=400, detail='Este agendamento não requer redistribuição')
    
    date = target_apt['date']
    time_slot = target_apt['time_slot']
    perm_field = f'can_{emission_system}'
    
    # Buscar agentes com permissão
    agents_with_perm = await db.users.find({
        'role': UserRole.AGENTE,
        'approved': True,
        perm_field: True
    }, {'_id': 0}).to_list(100)
    
    agent_ids_with_perm = [a['id'] for a in agents_with_perm]
    
    if not agent_ids_with_perm:
        return RedistributionResult(
            success=False,
            message=f'Não há agentes com permissão para {emission_system.upper()}'
        )
    
    # Buscar um agendamento comum que pode ser movido
    # (agendamento de um agente com permissão, mas sem emission_system)
    movable_apt = await db.appointments.find_one({
        'date': date,
        'time_slot': time_slot,
        'user_id': {'$in': agent_ids_with_perm},
        '$or': [
            {'emission_system': None},
            {'emission_system': {'$exists': False}}
        ],
        'status': {'$nin': ['cancelado', 'pendente_atribuicao', 'emitido']}
    }, {'_id': 0})
    
    if not movable_apt:
        return RedistributionResult(
            success=False,
            message='Não há agendamentos comuns que possam ser redistribuídos neste horário'
        )
    
    # Buscar um agente sem permissão que esteja livre
    agents_without_perm = await db.users.find({
        'role': UserRole.AGENTE,
        'approved': True,
        '$or': [
            {perm_field: False},
            {perm_field: {'$exists': False}}
        ]
    }, {'_id': 0}).to_list(100)
    
    available_agent = None
    for agent in agents_without_perm:
        # Verificar se o agente está livre neste horário
        existing = await db.appointments.find_one({
            'user_id': agent['id'],
            'date': date,
            'time_slot': time_slot,
            'status': {'$nin': ['cancelado', 'pendente_atribuicao']}
        }, {'_id': 0})
        
        if not existing:
            available_agent = agent
            break
    
    if not available_agent:
        return RedistributionResult(
            success=False,
            message='Não há agentes disponíveis para receber a redistribuição'
        )
    
    # Realizar a redistribuição
    freed_agent_id = movable_apt['user_id']
    freed_agent = next((a for a in agents_with_perm if a['id'] == freed_agent_id), None)
    freed_agent_name = freed_agent['name'] if freed_agent else 'Desconhecido'
    
    now_str = datetime.now(timezone.utc).isoformat()
    
    # 1. Mover o agendamento comum para o novo agente
    await db.appointments.update_one(
        {'id': movable_apt['id']},
        {'$set': {
            'user_id': available_agent['id'],
            'updated_at': now_str
        }}
    )
    
    # Registrar histórico da movimentação
    await log_appointment_history(
        movable_apt['id'],
        'redistributed',
        current_user.id,
        current_user.name,
        field_changed='user_id',
        old_value=freed_agent_name,
        new_value=available_agent['name']
    )
    
    # 2. Atribuir o agendamento especial ao agente liberado
    await db.appointments.update_one(
        {'id': request.target_appointment_id},
        {'$set': {
            'user_id': freed_agent_id,
            'status': 'confirmado',
            'updated_at': now_str
        }}
    )
    
    # Registrar histórico da atribuição
    await log_appointment_history(
        request.target_appointment_id,
        'assigned',
        current_user.id,
        current_user.name,
        field_changed='user_id',
        old_value=None,
        new_value=freed_agent_name
    )
    
    # Notificar os agentes afetados
    # Notificar agente que recebeu o agendamento movido
    await db.notifications.insert_one({
        'id': str(uuid.uuid4()),
        'user_id': available_agent['id'],
        'message': f'Agendamento transferido para você: {movable_apt["first_name"]} {movable_apt["last_name"]}',
        'type': 'appointment_transferred',
        'read': False,
        'created_at': now_str
    })
    
    # Notificar agente com permissão sobre o novo agendamento especial
    await db.notifications.insert_one({
        'id': str(uuid.uuid4()),
        'user_id': freed_agent_id,
        'message': f'[{emission_system.upper()}] Novo agendamento: {target_apt["first_name"]} {target_apt["last_name"]}',
        'type': 'appointment_assigned',
        'read': False,
        'created_at': now_str
    })
    
    # Remover notificações de pendente
    await db.notifications.delete_many({
        'appointment_id': request.target_appointment_id,
        'type': 'pending_assignment'
    })
    
    return RedistributionResult(
        success=True,
        message=f'Redistribuição realizada com sucesso',
        moved_appointment_id=movable_apt['id'],
        freed_agent_id=freed_agent_id,
        freed_agent_name=freed_agent_name,
        new_agent_id=available_agent['id'],
        new_agent_name=available_agent['name']
    )

@api_router.get('/appointments/check-redistribution/{apt_id}')
async def check_redistribution_possible(
    apt_id: str,
    current_user: User = Depends(get_current_user)
):
    """Verificar se é possível fazer redistribuição para um agendamento especial"""
    apt = await db.appointments.find_one({'id': apt_id}, {'_id': 0})
    if not apt:
        raise HTTPException(status_code=404, detail='Agendamento não encontrado')
    
    emission_system = apt.get('emission_system')
    if not emission_system:
        return {'can_redistribute': False, 'reason': 'Agendamento não requer sistema especial'}
    
    date = apt['date']
    time_slot = apt['time_slot']
    perm_field = f'can_{emission_system}'
    
    # Buscar agentes com permissão disponíveis diretamente
    agents_with_perm = await db.users.find({
        'role': UserRole.AGENTE,
        'approved': True,
        perm_field: True
    }, {'_id': 0}).to_list(100)
    
    agent_ids_with_perm = [a['id'] for a in agents_with_perm]
    
    for agent in agents_with_perm:
        existing = await db.appointments.find_one({
            'user_id': agent['id'],
            'date': date,
            'time_slot': time_slot,
            'status': {'$nin': ['cancelado', 'pendente_atribuicao']}
        }, {'_id': 0})
        
        if not existing:
            return {
                'can_redistribute': False,
                'reason': 'Há agentes com permissão disponíveis diretamente',
                'available_agent': {'id': agent['id'], 'name': agent['name']}
            }
    
    # Verificar se há agendamentos comuns que podem ser movidos
    movable_count = await db.appointments.count_documents({
        'date': date,
        'time_slot': time_slot,
        'user_id': {'$in': agent_ids_with_perm},
        '$or': [
            {'emission_system': None},
            {'emission_system': {'$exists': False}}
        ],
        'status': {'$nin': ['cancelado', 'pendente_atribuicao', 'emitido']}
    })
    
    if movable_count == 0:
        return {
            'can_redistribute': False,
            'reason': f'Todos os agentes com permissão {emission_system.upper()} estão ocupados com atendimentos especiais'
        }
    
    # Verificar se há agentes sem permissão disponíveis
    agents_without_perm = await db.users.find({
        'role': UserRole.AGENTE,
        'approved': True,
        '$or': [
            {perm_field: False},
            {perm_field: {'$exists': False}}
        ]
    }, {'_id': 0}).to_list(100)
    
    for agent in agents_without_perm:
        existing = await db.appointments.find_one({
            'user_id': agent['id'],
            'date': date,
            'time_slot': time_slot,
            'status': {'$nin': ['cancelado', 'pendente_atribuicao']}
        }, {'_id': 0})
        
        if not existing:
            return {
                'can_redistribute': True,
                'reason': f'É possível mover um agendamento comum para liberar um agente {emission_system.upper()}',
                'movable_count': movable_count
            }
    
    return {
        'can_redistribute': False,
        'reason': 'Todos os agentes estão ocupados'
    }

@api_router.get('/appointments/paginated')
async def get_appointments_paginated(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    date: Optional[str] = None,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Endpoint com paginação para agendamentos"""
    query = {}
    
    if current_user.role == UserRole.AGENTE:
        query['user_id'] = current_user.id
    
    if date:
        query['date'] = date
    if status:
        query['status'] = status
    if user_id and current_user.role in [UserRole.ADMIN, UserRole.SUPERVISOR]:
        query['user_id'] = user_id
    
    # Contar total
    total = await db.appointments.count_documents(query)
    
    # Buscar página
    skip = (page - 1) * page_size
    appointments = await db.appointments.find(query, {'_id': 0}) \
        .sort('time_slot', 1) \
        .skip(skip) \
        .limit(page_size) \
        .to_list(page_size)
    
    return {
        'items': [Appointment(**apt) for apt in appointments],
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size
    }

@api_router.get('/appointments/pending', response_model=List[Appointment])
async def get_pending_appointments(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail='Apenas supervisores têm acesso aos agendamentos pendentes')
    
    appointments = await db.appointments.find({
        'status': 'pendente_atribuicao'
    }, {'_id': 0}).sort('created_at', -1).to_list(1000)
    
    return [Appointment(**apt) for apt in appointments]

@api_router.get('/appointments/availability')
async def check_availability(
    date: str,
    time_slot: str,
    current_user: User = Depends(get_current_user)
):
    agents = await db.users.find({'role': UserRole.AGENTE, 'approved': True}, {'_id': 0}).to_list(100)
    
    availability = []
    for agent in agents:
        existing = await db.appointments.find_one({
            'user_id': agent['id'],
            'date': date,
            'time_slot': time_slot,
            'status': {'$ne': 'cancelado'}
        }, {'_id': 0})
        
        reserved = await db.appointments.find_one({
            'date': date,
            'time_slot': time_slot,
            'status': 'pendente_atribuicao'
        }, {'_id': 0})
        
        availability.append({
            'agent_id': agent['id'],
            'agent_name': agent['name'],
            'available': existing is None and reserved is None
        })
    
    total_agents = len(agents)
    available_agents = sum(1 for a in availability if a['available'])
    
    reserved_count = await db.appointments.count_documents({
        'date': date,
        'time_slot': time_slot,
        'status': 'pendente_atribuicao'
    })
    
    return {
        'date': date,
        'time_slot': time_slot,
        'total_agents': total_agents,
        'available_agents': available_agents,
        'reserved_count': reserved_count,
        'can_schedule': available_agents > 0,
        'agents': availability
    }

@api_router.post('/appointments/{apt_id}/upload')
async def upload_document(
    apt_id: str,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user)
):
    apt = await db.appointments.find_one({'id': apt_id}, {'_id': 0})
    if not apt:
        raise HTTPException(status_code=404, detail='Appointment not found')
    
    uploaded_filenames = []
    
    for file in files:
        file_ext = Path(file.filename).suffix
        filename = f"{apt_id}_{uuid.uuid4()}{file_ext}"
        file_path = UPLOAD_DIR / filename
        
        with open(file_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        uploaded_filenames.append(filename)
    
    current_urls = apt.get('document_urls', [])
    new_urls = current_urls + uploaded_filenames
    
    await db.appointments.update_one(
        {'id': apt_id},
        {'$set': {'document_urls': new_urls}}
    )
    
    return {'message': f'{len(files)} file(s) uploaded successfully', 'filenames': uploaded_filenames}

@api_router.get('/appointments/{apt_id}/download/{filename}')
async def download_document(apt_id: str, filename: str, current_user: User = Depends(get_current_user)):
    apt = await db.appointments.find_one({'id': apt_id}, {'_id': 0})
    if not apt or filename not in apt.get('document_urls', []):
        raise HTTPException(status_code=404, detail='Document not found')
    
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail='File not found')
    
    return FileResponse(file_path, filename=filename)

@api_router.delete('/appointments/{apt_id}/document/{filename}')
async def delete_document(apt_id: str, filename: str, current_user: User = Depends(get_current_user)):
    apt = await db.appointments.find_one({'id': apt_id}, {'_id': 0})
    if not apt or filename not in apt.get('document_urls', []):
        raise HTTPException(status_code=404, detail='Document not found')
    
    file_path = UPLOAD_DIR / filename
    if file_path.exists():
        file_path.unlink()
    
    current_urls = apt.get('document_urls', [])
    new_urls = [url for url in current_urls if url != filename]
    
    await db.appointments.update_one(
        {'id': apt_id},
        {'$set': {'document_urls': new_urls}}
    )
    
    return {'message': 'Document deleted successfully'}

@api_router.get('/appointments/available-slots')
async def get_available_slots(
    date: str, 
    emission_system: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Obter horários disponíveis para uma data.
    Se emission_system for especificado (safeweb/serpro), retorna apenas
    horários onde há agentes com permissão disponíveis.
    """
    now_br = datetime.now(BR_TZ)
    today_br = now_br.date().isoformat()
    current_time_br = now_br.strftime('%H:%M')
    target_date = datetime.fromisoformat(date).date()
    
    # Validar emission_system
    if emission_system and emission_system not in ['safeweb', 'serpro']:
        raise HTTPException(status_code=400, detail='Sistema de emissão inválido')
    
    # Horários normais (sem hora extra)
    normal_time_slots = [
        '08:00', '08:20', '08:40',
        '09:00', '09:20', '09:40',
        '10:00', '10:20', '10:40',
        '11:00', '11:20', '11:40',
        '12:00', '12:20',
        '13:00', '13:20', '13:40',
        '14:00', '14:20', '14:40',
        '15:00', '15:20', '15:40',
        '16:00', '16:20', '16:40',
        '17:00', '17:20', '17:40'
    ]
    
    # Buscar horários extras ativados para esta data
    extra_hours_doc = await db.extra_hours.find_one({'date': date})
    extra_slots = extra_hours_doc.get('slots', []) if extra_hours_doc else []
    
    # Combinar horários normais + extras ativados
    time_slots = normal_time_slots + extra_slots
    time_slots = sorted(set(time_slots))  # Remover duplicados e ordenar
    
    # Buscar agentes
    agent_query = {'role': UserRole.AGENTE, 'approved': True}
    if emission_system:
        agent_query[f'can_{emission_system}'] = True
    
    agents = await db.users.find(agent_query, {'_id': 0}).to_list(100)
    agent_ids = [a['id'] for a in agents]
    total_agents_with_permission = len(agents)
    
    # Também buscar total geral de agentes para calcular disponibilidade de redistribuição
    all_agents = await db.users.find({'role': UserRole.AGENTE, 'approved': True}, {'_id': 0}).to_list(100)
    total_all_agents = len(all_agents)
    
    available_slots = []
    
    for slot in time_slots:
        slot_datetime = datetime.fromisoformat(f"{date}T{slot}:00").replace(tzinfo=BR_TZ)
        # Se a data for hoje, filtrar horários passados usando current_time_br
        if date == today_br and slot < current_time_br:
            continue
        # Se a data for anterior a hoje, pula todos os slots
        if date < today_br:
            continue
        
        if total_all_agents == 0:
            continue
        
        # Contar ocupação total
        occupied_total = await db.appointments.count_documents({
            'date': date,
            'time_slot': slot,
            'status': {'$nin': ['cancelado', 'pendente_atribuicao']}
        })
        
        reserved = await db.appointments.count_documents({
            'date': date,
            'time_slot': slot,
            'status': 'pendente_atribuicao'
        })
        
        if emission_system:
            # Se precisa de permissão especial, verificar agentes com permissão disponíveis
            occupied_with_permission = await db.appointments.count_documents({
                'date': date,
                'time_slot': slot,
                'user_id': {'$in': agent_ids},
                'status': {'$nin': ['cancelado', 'pendente_atribuicao']}
            })
            
            available_with_permission = total_agents_with_permission - occupied_with_permission
            
            # Verificar se há possibilidade de redistribuição
            # Se agentes com permissão estão ocupados mas com atendimentos comuns,
            # podemos redistribuir esses atendimentos para liberar o agente
            can_redistribute = False
            if available_with_permission <= 0 and total_agents_with_permission > 0:
                # Buscar agendamentos comuns (sem emission_system) de agentes com permissão
                redistributable = await db.appointments.count_documents({
                    'date': date,
                    'time_slot': slot,
                    'user_id': {'$in': agent_ids},
                    '$or': [
                        {'emission_system': None},
                        {'emission_system': {'$exists': False}}
                    ],
                    'status': {'$nin': ['cancelado', 'pendente_atribuicao']}
                })
                
                # Verificar se há agentes sem permissão disponíveis para receber redistribuição
                agents_without_permission = await db.users.count_documents({
                    'role': UserRole.AGENTE,
                    'approved': True,
                    f'can_{emission_system}': {'$ne': True}
                })
                
                occupied_without_permission = await db.appointments.count_documents({
                    'date': date,
                    'time_slot': slot,
                    'user_id': {'$nin': agent_ids},
                    'status': {'$nin': ['cancelado', 'pendente_atribuicao']}
                })
                
                available_without_permission = agents_without_permission - occupied_without_permission
                
                if redistributable > 0 and available_without_permission > 0:
                    can_redistribute = True
            
            if available_with_permission > 0 or can_redistribute:
                available_slots.append({
                    'time_slot': slot,
                    'available_agents': max(0, available_with_permission),
                    'total_agents': total_agents_with_permission,
                    'reserved': reserved,
                    'status': 'available' if available_with_permission > 0 else 'redistribution_needed',
                    'can_redistribute': can_redistribute,
                    'requires_permission': emission_system
                })
        else:
            # Sem requisito especial, calcular normalmente
            available = total_all_agents - occupied_total
            
            if available > 0:
                available_slots.append({
                    'time_slot': slot,
                    'available_agents': available,
                    'total_agents': total_all_agents,
                    'reserved': reserved,
                    'status': 'available'
                })
    
    return {
        'date': date,
        'emission_system': emission_system,
        'total_agents_with_permission': total_agents_with_permission if emission_system else total_all_agents,
        'available_slots': available_slots
    }

@api_router.get('/appointments/filtered')
async def get_filtered_appointments(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    agent_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Buscar agendamentos com filtros avançados"""
    query = {}
    
    # Agentes só veem seus próprios agendamentos
    if current_user.role == UserRole.AGENTE:
        query['user_id'] = current_user.id
    elif agent_id:
        query['user_id'] = agent_id
    
    # Filtro por intervalo de datas
    if date_from and date_to:
        query['date'] = {'$gte': date_from, '$lte': date_to}
    elif date_from:
        query['date'] = {'$gte': date_from}
    elif date_to:
        query['date'] = {'$lte': date_to}
    
    # Filtro por status
    if status:
        query['status'] = status
    
    # Busca por nome ou protocolo
    if search:
        query['$or'] = [
            {'first_name': {'$regex': search, '$options': 'i'}},
            {'last_name': {'$regex': search, '$options': 'i'}},
            {'protocol_number': {'$regex': search, '$options': 'i'}}
        ]
    
    appointments = await db.appointments.find(query, {'_id': 0}).sort([('date', -1), ('time_slot', 1)]).to_list(500)
    return [Appointment(**apt) for apt in appointments]

@api_router.get('/appointments/{apt_id}', response_model=Appointment)
async def get_appointment(apt_id: str, current_user: User = Depends(get_current_user)):
    apt = await db.appointments.find_one({'id': apt_id}, {'_id': 0})
    if not apt:
        raise HTTPException(status_code=404, detail='Appointment not found')
    return Appointment(**apt)

@api_router.put('/appointments/{apt_id}', response_model=Appointment)
async def update_appointment(
    apt_id: str,
    apt_data: AppointmentUpdate,
    current_user: User = Depends(get_current_user)
):

    block_admin(current_user)
    apt = await db.appointments.find_one({'id': apt_id}, {'_id': 0})
    if not apt:
        raise HTTPException(status_code=404, detail='Appointment not found')

    # SUPERVISOR pode editar diretamente
    if current_user.role == UserRole.SUPERVISOR:

        update_data = {k: v for k, v in apt_data.model_dump().items() if v is not None}
        update_data['updated_at'] = datetime.now(timezone.utc).isoformat()

        # Validação: se status for 'reagendar', reschedule_reason é obrigatório e padronizado
        if update_data.get('status') == 'reagendar':
            allowed_reasons = [
                'cliente_sem_documento',
                'cliente_nao_compareceu',
                'dados_incorretos',
                'problema_biometria',
                'instabilidade_sistema',
                'solicitacao_cliente',
                'outros'
            ]
            reason = update_data.get('reschedule_reason')
            if not reason or reason not in allowed_reasons:
                raise HTTPException(status_code=400, detail='Motivo do reagendamento é obrigatório e deve ser um valor válido.')
        # Para outros status, pode ficar vazio

        if current_user.role == UserRole.AGENTE:
            validate_agent_update_fields(update_data, apt, current_user)
        elif current_user.role in [UserRole.TELEVENDAS, UserRole.COMERCIAL]:
            validate_no_agent_assignment(update_data, current_user)
        # SUPERVISOR pode tudo


        for field, new_value in update_data.items():
            if field == 'updated_at':
                continue
            old_value = apt.get(field)
            if old_value != new_value:
                action = 'status_changed' if field == 'status' else 'updated'
                if field == 'time_slot' or field == 'date':
                    action = 'rescheduled'
                # Se for status 'reagendar', registra motivo no histórico
                if field == 'status' and new_value == 'reagendar':
                    await log_appointment_history(
                        apt_id,
                        action,
                        current_user.id,
                        current_user.name,
                        field_changed='reschedule_reason',
                        old_value=None,
                        new_value=update_data.get('reschedule_reason')
                    )
                await log_appointment_history(
                    apt_id,
                    action,
                    current_user.id,
                    current_user.name,
                    field_changed=field,
                    old_value=str(old_value) if old_value is not None else None,
                    new_value=str(new_value)
                )

        if apt_data.status == 'emitido' and apt.get('document_urls'):
            for filename in apt.get('document_urls', []):
                file_path = UPLOAD_DIR / filename
                if file_path.exists():
                    file_path.unlink()
            update_data['document_urls'] = []

        await db.appointments.update_one({'id': apt_id}, {'$set': update_data})
        updated_apt = await db.appointments.find_one({'id': apt_id}, {'_id': 0})
        return Appointment(**updated_apt)

    # Criador ou agente designado pode solicitar alteração via change-request
    if current_user.id == apt.get('created_by') or current_user.id == apt.get('user_id'):
        change_req = {
            'id': str(uuid.uuid4()),
            'appointment_id': apt_id,
            'request_type': ChangeRequestType.EDIT,
            'status': ChangeRequestStatus.PENDING,
            'reason': apt_data.notes if apt_data.notes else None,
            'new_first_name': apt_data.first_name,
            'new_last_name': apt_data.last_name,
            'new_protocol_number': apt_data.protocol_number,
            'new_additional_protocols': apt_data.additional_protocols,
            'new_date': apt_data.date,
            'new_time_slot': apt_data.time_slot,
            'new_notes': apt_data.notes,
            'requested_by': current_user.id,
            'requested_by_name': current_user.name,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        await db.change_requests.insert_one(change_req)
        return {
            'message': 'Solicitação de alteração enviada para aprovação do supervisor',
            'change_request_id': change_req['id']
        }

    # Outros perfis não podem editar
    raise HTTPException(status_code=403, detail='Apenas supervisor ou criador pode solicitar alteração')

@api_router.delete('/appointments/{apt_id}')
async def delete_appointment(apt_id: str, current_user: User = Depends(get_current_user)):
    apt = await db.appointments.find_one({'id': apt_id}, {'_id': 0})
    if not apt:
        raise HTTPException(status_code=404, detail='Appointment not found')

    # SUPERVISOR pode cancelar diretamente
    if current_user.role == UserRole.SUPERVISOR:
        result = await db.appointments.delete_one({'id': apt_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail='Appointment not found')
        return {'message': 'Appointment deleted'}

    # Criador pode solicitar cancelamento via change-request
    if current_user.id == apt.get('created_by'):
        change_req = {
            'id': str(uuid.uuid4()),
            'appointment_id': apt_id,
            'request_type': ChangeRequestType.CANCEL,
            'status': ChangeRequestStatus.PENDING,
            'reason': 'Solicitação de cancelamento',
            'requested_by': current_user.id,
            'requested_by_name': current_user.name,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        await db.change_requests.insert_one(change_req)
        return {
            'message': 'Solicitação de cancelamento enviada para aprovação do supervisor',
            'change_request_id': change_req['id']
        }

    # Outros perfis não podem cancelar
    raise HTTPException(status_code=403, detail='Apenas supervisor ou criador pode solicitar cancelamento')

@api_router.get('/notifications', response_model=List[Notification])
async def get_notifications(
    read: Optional[bool] = None,
    current_user: User = Depends(get_current_user)
):
    query = {'user_id': current_user.id}
    if read is not None:
        query['read'] = read
    
    notifications = await db.notifications.find(query, {'_id': 0}).sort('created_at', -1).to_list(100)
    return [Notification(**n) for n in notifications]

@api_router.put('/notifications/{notif_id}/read')
async def mark_notification_read(notif_id: str, current_user: User = Depends(get_current_user)):
    await db.notifications.update_one(
        {'id': notif_id, 'user_id': current_user.id},
        {'$set': {'read': True}}
    )
    return {'message': 'Notification marked as read'}

@api_router.put('/notifications/read-all')
async def mark_all_notifications_read(current_user: User = Depends(get_current_user)):
    """Marcar todas as notificações como lidas"""
    result = await db.notifications.update_many(
        {'user_id': current_user.id, 'read': False},
        {'$set': {'read': True}}
    )
    return {'message': f'{result.modified_count} notifications marked as read'}

@api_router.delete('/notifications/{notif_id}')
async def delete_notification(notif_id: str, current_user: User = Depends(get_current_user)):
    """Excluir uma notificação"""
    result = await db.notifications.delete_one({
        'id': notif_id, 
        'user_id': current_user.id
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Notification not found')
    return {'message': 'Notification deleted'}

@api_router.delete('/notifications')
async def delete_all_read_notifications(current_user: User = Depends(get_current_user)):
    """Excluir todas as notificações lidas"""
    result = await db.notifications.delete_many({
        'user_id': current_user.id,
        'read': True
    })
    return {'message': f'{result.deleted_count} notifications deleted'}

@api_router.get('/stats/dashboard')
async def get_dashboard_stats(
    date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Estatísticas para o dashboard"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERVISOR]:
        raise HTTPException(status_code=403, detail='Not authorized')
    
    target_date = date or datetime.now(timezone.utc).date().isoformat()
    
    # Total de agendamentos do dia
    total = await db.appointments.count_documents({'date': target_date})
    
    # Por status
    pendentes = await db.appointments.count_documents({'date': target_date, 'status': 'pendente_atribuicao'})
    confirmados = await db.appointments.count_documents({'date': target_date, 'status': 'confirmado'})
    emitidos = await db.appointments.count_documents({'date': target_date, 'status': 'emitido'})
    reagendar = await db.appointments.count_documents({'date': target_date, 'status': 'reagendar'})
    presencial = await db.appointments.count_documents({'date': target_date, 'status': 'presencial'})
    cancelados = await db.appointments.count_documents({'date': target_date, 'status': 'cancelado'})
    
    # Auto-atribuídos
    auto_assigned = await db.appointments.count_documents({'date': target_date, 'auto_assigned': True})
    
    # Carga por agente
    agents = await db.users.find({'role': UserRole.AGENTE, 'approved': True}, {'_id': 0}).to_list(100)
    agent_stats = []
    for agent in agents:
        count = await db.appointments.count_documents({
            'user_id': agent['id'],
            'date': target_date,
            'status': {'$ne': 'cancelado'}
        })
        agent_stats.append({
            'id': agent['id'],
            'name': agent['name'],
            'appointments': count
        })
    
    return {
        'date': target_date,
        'total': total,
        'by_status': {
            'pendentes': pendentes,
            'confirmados': confirmados,
            'emitidos': emitidos,
            'reagendar': reagendar,
            'presencial': presencial,
            'cancelados': cancelados
        },
        'auto_assigned': auto_assigned,
        'agents': agent_stats
    }

# ============== PRESENCE SYSTEM ==============

@api_router.post('/presence/heartbeat')
async def send_heartbeat(current_user: User = Depends(get_current_user)):
    """Enviar heartbeat para manter status online"""
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {'id': current_user.id},
        {'$set': {'is_online': True, 'last_seen': now}}
    )
    return {'status': 'online', 'timestamp': now}

@api_router.post('/presence/offline')
async def go_offline(current_user: User = Depends(get_current_user)):
    """Marcar usuário como offline (ao fazer logout)"""
    await db.users.update_one(
        {'id': current_user.id},
        {'$set': {'is_online': False, 'last_seen': datetime.now(timezone.utc).isoformat()}}
    )
    return {'status': 'offline'}

@api_router.get('/presence/agents')
async def get_agents_presence(current_user: User = Depends(get_current_user)):
    """Obter status de presença de todos os agentes"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERVISOR]:
        raise HTTPException(status_code=403, detail='Not authorized')
    
    agents = await db.users.find({
        'role': UserRole.AGENTE, 
        'approved': True
    }, {'_id': 0, 'password_hash': 0}).to_list(100)
    
    now = datetime.now(timezone.utc)
    result = []
    for agent in agents:
        last_seen = agent.get('last_seen')
        is_online = agent.get('is_online', False)
        
        # Verificar se está realmente online (heartbeat recente)
        if last_seen and is_online:
            last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
            minutes_ago = (now - last_seen_dt).total_seconds() / 60
            if minutes_ago > PRESENCE_TIMEOUT_MINUTES:
                is_online = False
        
        result.append({
            'id': agent['id'],
            'name': agent['name'],
            'email': agent['email'],
            'is_online': is_online,
            'last_seen': last_seen
        })
    
    return result

# ============== REPORTS SYSTEM ==============

@api_router.get('/reports/daily')
async def get_daily_report(
    date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Gerar relatório diário de atendimentos"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERVISOR]:
        raise HTTPException(status_code=403, detail='Not authorized')
    
    target_date = date or datetime.now(timezone.utc).date().isoformat()
    
    # Buscar todos os agendamentos do dia
    appointments = await db.appointments.find({
        'date': target_date
    }, {'_id': 0}).to_list(1000)
    
    # Estatísticas gerais
    total = len(appointments)
    by_status = {}
    for apt in appointments:
        status = apt.get('status', 'unknown')
        by_status[status] = by_status.get(status, 0) + 1
    
    # Por agente
    agents = await db.users.find({'role': UserRole.AGENTE, 'approved': True}, {'_id': 0}).to_list(100)
    agent_reports = []
    
    for agent in agents:
        agent_apts = [a for a in appointments if a.get('user_id') == agent['id']]
        agent_by_status = {}
        for apt in agent_apts:
            status = apt.get('status', 'unknown')
            agent_by_status[status] = agent_by_status.get(status, 0) + 1
        
        # Calcular horas trabalhadas (20 min por atendimento emitido)
        emitidos = agent_by_status.get('emitido', 0)
        hours_worked = (emitidos * 20) / 60
        
        agent_reports.append({
            'id': agent['id'],
            'name': agent['name'],
            'total': len(agent_apts),
            'by_status': agent_by_status,
            'hours_worked': round(hours_worked, 2)
        })
    
    # Calcular totais
    total_emitidos = by_status.get('emitido', 0)
    total_hours = (total_emitidos * 20) / 60
    
    return {
        'date': target_date,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'summary': {
            'total_appointments': total,
            'by_status': by_status,
            'total_hours_worked': round(total_hours, 2),
            'auto_assigned': len([a for a in appointments if a.get('auto_assigned')])
        },
        'agents': agent_reports
    }

@api_router.get('/reports/weekly-hours')
async def get_weekly_hours(
    current_user: User = Depends(get_current_user)
):
    """Calcular saldo de horas da semana por agente"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERVISOR]:
        raise HTTPException(status_code=403, detail='Not authorized')
    
    now = datetime.now(timezone.utc)
    # Calcular início da semana (segunda-feira)
    start_of_week = now - timedelta(days=now.weekday())
    start_date = start_of_week.date().isoformat()
    end_date = now.date().isoformat()
    
    agents = await db.users.find({'role': UserRole.AGENTE, 'approved': True}, {'_id': 0}).to_list(100)
    
    weekly_report = []
    for agent in agents:
        # Buscar agendamentos emitidos na semana
        emitidos = await db.appointments.count_documents({
            'user_id': agent['id'],
            'date': {'$gte': start_date, '$lte': end_date},
            'status': 'emitido'
        })
        
        # Calcular horas (20 min por atendimento)
        hours_worked = (emitidos * 20) / 60
        
        # Meta semanal padrão: 40 horas
        weekly_target = 40
        balance = hours_worked - weekly_target
        
        weekly_report.append({
            'id': agent['id'],
            'name': agent['name'],
            'emitidos': emitidos,
            'hours_worked': round(hours_worked, 2),
            'weekly_target': weekly_target,
            'balance': round(balance, 2),
            'is_online': agent.get('is_online', False)
        })
    
    return {
        'week_start': start_date,
        'week_end': end_date,
        'generated_at': now.isoformat(),
        'agents': weekly_report
    }

# ============== EXTRA HOURS MANAGEMENT ==============

EXTRA_TIME_SLOTS = ['07:40', '12:40', '18:00', '18:20', '18:40']

@api_router.get('/extra-hours')
async def get_extra_hours(
    date: str,
    current_user: User = Depends(get_current_user)
):
    """Obter horários extras ativados para uma data"""
    doc = await db.extra_hours.find_one({'date': date}, {'_id': 0})
    return {
        'date': date,
        'available_slots': EXTRA_TIME_SLOTS,
        'active_slots': doc.get('slots', []) if doc else []
    }

@api_router.put('/extra-hours')
async def update_extra_hours(
    date: str,
    slots: List[str] = Query(default=[]),
    current_user: User = Depends(get_current_user)
):
    """Ativar/desativar horários extras para uma data (apenas supervisor)"""
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail='Apenas supervisores podem gerenciar horários extras')
    
    # Validar slots - aceitar tanto query params
    valid_slots = [s for s in slots if s in EXTRA_TIME_SLOTS]
    
    await db.extra_hours.update_one(
        {'date': date},
        {'$set': {'date': date, 'slots': valid_slots, 'updated_by': current_user.id, 'updated_at': datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    
    return {
        'date': date,
        'active_slots': valid_slots,
        'message': f'{len(valid_slots)} horário(s) extra(s) ativado(s)'
    }

@api_router.get('/slots/all')
async def get_all_slots(
    date: str,
    current_user: User = Depends(get_current_user)
):
    """Obter todos os slots do dia (normais + extras) com status de ocupação"""
    # Horários normais
    normal_slots = [
        '08:00', '08:20', '08:40',
        '09:00', '09:20', '09:40',
        '10:00', '10:20', '10:40',
        '11:00', '11:20', '11:40',
        '12:00', '12:20',
        '13:00', '13:20', '13:40',
        '14:00', '14:20', '14:40',
        '15:00', '15:20', '15:40',
        '16:00', '16:20', '16:40',
        '17:00', '17:20', '17:40'
    ]
    
    # Horários extras ativados
    extra_doc = await db.extra_hours.find_one({'date': date})
    extra_slots = extra_doc.get('slots', []) if extra_doc else []
    
    all_slots = sorted(set(normal_slots + extra_slots))
    
    # Buscar agentes
    agents = await db.users.find({'role': UserRole.AGENTE, 'approved': True}, {'_id': 0}).to_list(100)
    total_agents = len(agents)
    
    now_br = datetime.now(BR_TZ)
    today = now_br.date().isoformat()
    current_time = now_br.strftime('%H:%M')
    
    result = []
    for slot in all_slots:
        # Buscar agendamentos neste slot
        appointments = await db.appointments.find({
            'date': date,
            'time_slot': slot,
            'status': {'$ne': 'cancelado'}
        }, {'_id': 0}).to_list(100)
        
        # Contar por status
        occupied = len([a for a in appointments if a.get('status') != 'pendente_atribuicao'])
        pending = len([a for a in appointments if a.get('status') == 'pendente_atribuicao'])
        available = total_agents - occupied
        
        # Determinar se é horário atual
        is_current = date == today and slot == current_time[:5]
        is_past = date < today or (date == today and slot < current_time)
        is_extra = slot in EXTRA_TIME_SLOTS
        
        result.append({
            'time_slot': slot,
            'total_agents': total_agents,
            'occupied': occupied,
            'pending': pending,
            'available': max(0, available),
            'is_current': is_current,
            'is_past': is_past,
            'is_extra': is_extra,
            'appointments': appointments
        })
    
    return {
        'date': date,
        'total_agents': total_agents,
        'slots': result
    }

# ============== APPOINTMENT HISTORY SYSTEM ==============

async def log_appointment_history(
    appointment_id: str,
    action: str,
    changed_by: str,
    changed_by_name: str,
    field_changed: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None
):
    """Registra uma entrada no histórico do agendamento"""
    history_doc = {
        'id': str(uuid.uuid4()),
        'appointment_id': appointment_id,
        'action': action,
        'field_changed': field_changed,
        'old_value': old_value,
        'new_value': new_value,
        'changed_by': changed_by,
        'changed_by_name': changed_by_name,
        'changed_at': datetime.now(timezone.utc).isoformat()
    }
    await db.appointment_history.insert_one(history_doc)
    return history_doc

@api_router.get('/appointments/{apt_id}/history')
async def get_appointment_history(
    apt_id: str,
    current_user: User = Depends(get_current_user)
):
    """Obter histórico de alterações de um agendamento"""
    apt = await db.appointments.find_one({'id': apt_id}, {'_id': 0})
    if not apt:
        raise HTTPException(status_code=404, detail='Appointment not found')
    
    # Agentes só podem ver histórico dos seus próprios agendamentos
    if current_user.role == UserRole.AGENTE and apt.get('user_id') != current_user.id:
        raise HTTPException(status_code=403, detail='Not authorized')
    
    history = await db.appointment_history.find(
        {'appointment_id': apt_id}, 
        {'_id': 0}
    ).sort('changed_at', -1).to_list(100)
    
    return history

# ============== CSV EXPORT ==============

@api_router.get('/reports/daily/csv')
async def export_daily_report_csv(
    date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Exportar relatório diário em CSV"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERVISOR]:
        raise HTTPException(status_code=403, detail='Not authorized')
    
    target_date = date or datetime.now(timezone.utc).date().isoformat()
    
    # Buscar todos os agendamentos do dia
    appointments = await db.appointments.find({'date': target_date}, {'_id': 0}).to_list(1000)
    
    # Buscar nomes dos agentes
    agents = await db.users.find({'role': UserRole.AGENTE}, {'_id': 0}).to_list(100)
    agent_names = {a['id']: a['name'] for a in agents}
    
    # Criar CSV em memória
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Data', 'Horário', 'Nome', 'Sobrenome', 'Protocolo', 
        'Protocolos Adicionais', 'Status', 'Agente', 'Chat', 
        'Observações', 'Criado em'
    ])
    
    # Dados
    for apt in appointments:
        writer.writerow([
            apt.get('date', ''),
            apt.get('time_slot', ''),
            apt.get('first_name', ''),
            apt.get('last_name', ''),
            apt.get('protocol_number', ''),
            ', '.join(apt.get('additional_protocols', [])),
            apt.get('status', ''),
            agent_names.get(apt.get('user_id'), 'Não atribuído'),
            'Sim' if apt.get('has_chat') else 'Não',
            apt.get('notes', ''),
            apt.get('created_at', '')
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=relatorio_{target_date}.csv'
        }
    )

@api_router.get('/reports/weekly-hours/csv')
async def export_weekly_hours_csv(
    current_user: User = Depends(get_current_user)
):
    """Exportar saldo de horas semanal em CSV"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERVISOR]:
        raise HTTPException(status_code=403, detail='Not authorized')
    
    now = datetime.now(timezone.utc)
    start_of_week = now - timedelta(days=now.weekday())
    start_date = start_of_week.date().isoformat()
    end_date = now.date().isoformat()
    
    agents = await db.users.find({'role': UserRole.AGENTE, 'approved': True}, {'_id': 0}).to_list(100)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Agente', 'Email', 'Atendimentos Emitidos', 
        'Horas Trabalhadas', 'Meta Semanal', 'Saldo', 'Online'
    ])
    
    for agent in agents:
        emitidos = await db.appointments.count_documents({
            'user_id': agent['id'],
            'date': {'$gte': start_date, '$lte': end_date},
            'status': 'emitido'
        })
        
        hours_worked = (emitidos * 20) / 60
        weekly_target = 40
        balance = hours_worked - weekly_target
        
        writer.writerow([
            agent['name'],
            agent['email'],
            emitidos,
            round(hours_worked, 2),
            weekly_target,
            round(balance, 2),
            'Sim' if agent.get('is_online') else 'Não'
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=saldo_horas_{start_date}_{end_date}.csv'
        }
    )

# ============== RECURRING APPOINTMENTS ==============

@api_router.post('/appointments/recurring', response_model=Appointment)
async def create_recurring_appointment(
    apt_data: RecurringAppointmentCreate,
    current_user: User = Depends(get_current_user)
):
    block_admin(current_user)
    if current_user.role == UserRole.AGENTE:
        # Só pode reagendar o próprio e só pode mudar date/time_slot
        if apt_data.user_id != current_user.id:
            raise HTTPException(status_code=403, detail='AGENTE só pode reagendar o próprio agendamento')
        allowed_fields = {'date', 'time_slot', 'original_appointment_id', 'base_protocol', 'new_protocol'}
        for field in apt_data.model_dump():
            if field not in allowed_fields:
                raise HTTPException(status_code=403, detail='AGENTE só pode alterar data e horário no reagendamento')
    else:
        check_role_permission(current_user, [UserRole.TELEVENDAS, UserRole.COMERCIAL, UserRole.SUPERVISOR], 'reagendar')
    
    # Validar data
    apt_date = datetime.fromisoformat(apt_data.date)
    now = datetime.now(timezone.utc)
    today = now.date()
    
    if apt_date.date() < today:
        raise HTTPException(status_code=400, detail='Não é permitido agendar para dia anterior')
    

    # Interpreta o horário como America/Sao_Paulo (timezone-aware)
    BR_TZ = ZoneInfo("America/Sao_Paulo")
    apt_local = datetime.fromisoformat(f"{apt_data.date}T{apt_data.time_slot}:00").replace(tzinfo=BR_TZ)
    apt_utc = apt_local.astimezone(timezone.utc)

    if apt_utc <= now:
        raise HTTPException(status_code=400, detail='Não é permitido agendar para horário que já passou')
    
    # Calcular slots necessários
    total_protocols = 1 + len(apt_data.additional_protocols)
    slots_needed = 2 if total_protocols >= 3 else 1
    
    apt_id = str(uuid.uuid4())
    now_str = now.isoformat()
    
    # Criar nota com referência ao agendamento original
    notes = apt_data.notes or ''
    if apt_data.original_appointment_id:
        notes = f"[Reagendamento de {apt_data.base_protocol}] {notes}"
    
    apt_doc = {
        'id': apt_id,
        'user_id': None,
        'first_name': apt_data.first_name,
        'last_name': apt_data.last_name,
        'protocol_number': apt_data.new_protocol,  # Usa o NOVO protocolo
        'additional_protocols': apt_data.additional_protocols,
        'has_chat': apt_data.has_chat,
        'chat_platform': apt_data.chat_platform if apt_data.has_chat else None,
        'document_urls': [],
        'date': apt_data.date,
        'time_slot': apt_data.time_slot,
        'appointment_type': 'videoconferencia',
        'status': 'pendente_atribuicao',
        'notes': notes,
        'created_by': current_user.id,
        'created_at': now_str,
        'updated_at': now_str,
        'reserved_at': now_str,
        'slots_needed': slots_needed,
        'is_recurring': True,
        'original_appointment_id': apt_data.original_appointment_id,
        'base_protocol': apt_data.base_protocol  # Referência ao protocolo original
    }
    
    await db.appointments.insert_one(apt_doc)
    
    # Registrar no histórico
    await log_appointment_history(
        apt_id,
        'created',
        current_user.id,
        current_user.name,
        field_changed='recurring',
        old_value=apt_data.base_protocol,
        new_value=apt_data.new_protocol
    )
    
    # Se precisar de 2 slots, criar segundo agendamento
    if slots_needed == 2:
        # Corrigir: apt_datetime não definido, usar apt_local
        apt_local = datetime.fromisoformat(f"{apt_data.date}T{apt_data.time_slot}:00").replace(tzinfo=BR_TZ)
        next_slot_time = (apt_local + timedelta(minutes=20)).strftime('%H:%M')
        apt_id_2 = str(uuid.uuid4())
        apt_doc_2 = {
            'id': apt_id_2,
            'user_id': None,
            'first_name': apt_data.first_name,
            'last_name': apt_data.last_name,
            'protocol_number': apt_data.new_protocol,
            'additional_protocols': apt_data.additional_protocols,
            'has_chat': apt_data.has_chat,
            'chat_platform': apt_data.chat_platform if apt_data.has_chat else None,
            'document_urls': [],
            'date': apt_data.date,
            'time_slot': next_slot_time,
            'appointment_type': 'videoconferencia',
            'status': 'pendente_atribuicao',
            'notes': f'{notes} - PARTE 2/2',
            'created_by': current_user.id,
            'created_at': now_str,
            'updated_at': now_str,
            'reserved_at': now_str,
            'slots_needed': 2,
            'linked_appointment': apt_id,
            'is_recurring': True,
            'original_appointment_id': apt_data.original_appointment_id,
            'base_protocol': apt_data.base_protocol
        }
        
        await db.appointments.insert_one(apt_doc_2)
        await db.appointments.update_one({'id': apt_id}, {'$set': {'linked_appointment': apt_id_2}})
    
    # Notificar supervisores
    supervisors = await db.users.find({
        'role': {'$in': [UserRole.SUPERVISOR]}
    }, {'_id': 0}).to_list(100)
    
    for supervisor in supervisors:
        notif_doc = {
            'id': str(uuid.uuid4()),
            'user_id': supervisor['id'],
            'appointment_id': apt_id,
            'message': f'Novo reagendamento pendente: {apt_data.first_name} {apt_data.last_name} (Protocolo: {apt_data.new_protocol})',
            'type': 'pending_assignment',
            'read': False,
            'created_at': now_str
        }
        await db.notifications.insert_one(notif_doc)
    
    return Appointment(**apt_doc)

@api_router.get('/appointments/{apt_id}/recurring-info')
async def get_recurring_info(
    apt_id: str,
    current_user: User = Depends(get_current_user)
):
    """Obter informações de recorrência de um agendamento"""
    apt = await db.appointments.find_one({'id': apt_id}, {'_id': 0})
    if not apt:
        raise HTTPException(status_code=404, detail='Appointment not found')
    
    # Buscar agendamentos relacionados (mesmo cliente, diferentes protocolos)
    related = await db.appointments.find({
        'first_name': apt['first_name'],
        'last_name': apt['last_name'],
        'id': {'$ne': apt_id}
    }, {'_id': 0}).sort('date', -1).to_list(10)
    
    return {
        'current': apt,
        'is_recurring': apt.get('is_recurring', False),
        'original_appointment_id': apt.get('original_appointment_id'),
        'base_protocol': apt.get('base_protocol'),
        'related_appointments': related
    }

# ============== APPOINTMENT TEMPLATES ==============

@api_router.post('/templates', response_model=AppointmentTemplate)
async def create_template(
    template_data: AppointmentTemplateCreate,
    current_user: User = Depends(get_current_user)
):
    """Criar um novo template de agendamento"""
    if current_user.role not in [UserRole.TELEVENDAS, UserRole.COMERCIAL, UserRole.SUPERVISOR]:
        raise HTTPException(status_code=403, detail='Sem permissão para criar templates')
    
    now_str = datetime.now(timezone.utc).isoformat()
    template_id = str(uuid.uuid4())
    
    template_doc = {
        'id': template_id,
        'name': template_data.name,
        'client_first_name': template_data.client_first_name,
        'client_last_name': template_data.client_last_name,
        'preferred_time_slot': template_data.preferred_time_slot,
        'preferred_day_of_week': template_data.preferred_day_of_week,
        'has_chat': template_data.has_chat,
        'chat_platform': template_data.chat_platform if template_data.has_chat else None,
        'notes': template_data.notes,
        'tags': template_data.tags or [],
        'created_by': current_user.id,
        'created_at': now_str,
        'updated_at': now_str,
        'use_count': 0,
        'last_used_at': None
    }
    
    await db.appointment_templates.insert_one(template_doc)
    return AppointmentTemplate(**template_doc)

@api_router.get('/templates', response_model=List[AppointmentTemplate])
async def get_templates(
    search: Optional[str] = None,
    tag: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Listar templates de agendamento do usuário"""
    query = {'created_by': current_user.id}
    
    if search:
        query['$or'] = [
            {'name': {'$regex': search, '$options': 'i'}},
            {'client_first_name': {'$regex': search, '$options': 'i'}},
            {'client_last_name': {'$regex': search, '$options': 'i'}}
        ]
    
    if tag:
        query['tags'] = tag
    
    templates = await db.appointment_templates.find(
        query, {'_id': 0}
    ).sort('use_count', -1).to_list(100)
    
    return [AppointmentTemplate(**t) for t in templates]

@api_router.get('/templates/{template_id}', response_model=AppointmentTemplate)
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user)
):
    """Obter um template específico"""
    template = await db.appointment_templates.find_one(
        {'id': template_id, 'created_by': current_user.id}, 
        {'_id': 0}
    )
    if not template:
        raise HTTPException(status_code=404, detail='Template não encontrado')
    
    return AppointmentTemplate(**template)

@api_router.put('/templates/{template_id}', response_model=AppointmentTemplate)
async def update_template(
    template_id: str,
    template_data: AppointmentTemplateUpdate,
    current_user: User = Depends(get_current_user)
):
    """Atualizar um template"""
    template = await db.appointment_templates.find_one(
        {'id': template_id, 'created_by': current_user.id}, 
        {'_id': 0}
    )
    if not template:
        raise HTTPException(status_code=404, detail='Template não encontrado')
    
    update_data = {k: v for k, v in template_data.model_dump().items() if v is not None}
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.appointment_templates.update_one(
        {'id': template_id}, 
        {'$set': update_data}
    )
    
    updated = await db.appointment_templates.find_one({'id': template_id}, {'_id': 0})
    return AppointmentTemplate(**updated)

@api_router.delete('/templates/{template_id}')
async def delete_template(
    template_id: str,
    current_user: User = Depends(get_current_user)
):
    """Excluir um template"""
    result = await db.appointment_templates.delete_one(
        {'id': template_id, 'created_by': current_user.id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Template não encontrado')
    
    return {'message': 'Template excluído com sucesso'}

@api_router.post('/templates/{template_id}/use')
async def use_template(
    template_id: str,
    current_user: User = Depends(get_current_user)
):
    """Registrar uso de um template e retornar sugestão de agendamento"""
    template = await db.appointment_templates.find_one(
        {'id': template_id, 'created_by': current_user.id}, 
        {'_id': 0}
    )
    if not template:
        raise HTTPException(status_code=404, detail='Template não encontrado')
    
    # Incrementar contador de uso
    now = datetime.now(timezone.utc)
    await db.appointment_templates.update_one(
        {'id': template_id},
        {
            '$inc': {'use_count': 1},
            '$set': {'last_used_at': now.isoformat()}
        }
    )
    
    # Re-fetch template after update to get updated use_count
    updated_template = await db.appointment_templates.find_one(
        {'id': template_id}, 
        {'_id': 0}
    )
    
    # Buscar último agendamento deste cliente para sugerir próxima data
    last_appointment = await db.appointments.find_one(
        {
            'first_name': template['client_first_name'],
            'last_name': template['client_last_name']
        },
        {'_id': 0}
    )
    
    # Calcular próxima data sugerida
    suggested_date = None
    suggested_time = template.get('preferred_time_slot')
    
    if last_appointment:
        last_date = datetime.fromisoformat(last_appointment['date'])
        # Sugerir mesma data +1 semana
        suggested_date = (last_date + timedelta(days=7)).date().isoformat()
        if not suggested_time:
            suggested_time = last_appointment.get('time_slot')
    elif template.get('preferred_day_of_week') is not None:
        # Calcular próxima ocorrência do dia da semana preferido
        today = now.date()
        days_ahead = template['preferred_day_of_week'] - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        suggested_date = (today + timedelta(days=days_ahead)).isoformat()
    else:
        # Sugerir amanhã por padrão
        suggested_date = (now.date() + timedelta(days=1)).isoformat()
    
    return {
        'template': AppointmentTemplate(**updated_template),
        'suggestion': {
            'first_name': template['client_first_name'],
            'last_name': template['client_last_name'],
            'has_chat': template['has_chat'],
            'chat_platform': template.get('chat_platform'),
            'notes': template.get('notes', ''),
            'suggested_date': suggested_date,
            'suggested_time_slot': suggested_time,
            'last_appointment': {
                'date': last_appointment.get('date') if last_appointment else None,
                'time_slot': last_appointment.get('time_slot') if last_appointment else None,
                'protocol': last_appointment.get('protocol_number') if last_appointment else None
            } if last_appointment else None
        }
    }

@api_router.post('/templates/from-appointment/{apt_id}', response_model=AppointmentTemplate)
async def create_template_from_appointment(
    apt_id: str,
    template_name: str = Query(..., description="Nome do template"),
    current_user: User = Depends(get_current_user)
):
    """Criar um template a partir de um agendamento existente"""
    apt = await db.appointments.find_one({'id': apt_id}, {'_id': 0})
    if not apt:
        raise HTTPException(status_code=404, detail='Agendamento não encontrado')
    
    # Extrair dia da semana do agendamento
    apt_date = datetime.fromisoformat(apt['date'])
    day_of_week = apt_date.weekday()
    
    now_str = datetime.now(timezone.utc).isoformat()
    template_id = str(uuid.uuid4())
    
    template_doc = {
        'id': template_id,
        'name': template_name,
        'client_first_name': apt['first_name'],
        'client_last_name': apt['last_name'],
        'preferred_time_slot': apt.get('time_slot'),
        'preferred_day_of_week': day_of_week,
        'has_chat': apt.get('has_chat', False),
        'chat_platform': apt.get('chat_platform'),
        'notes': apt.get('notes', ''),
        'tags': [],
        'created_by': current_user.id,
        'created_at': now_str,
        'updated_at': now_str,
        'use_count': 0,
        'last_used_at': None
    }
    
    await db.appointment_templates.insert_one(template_doc)
    return AppointmentTemplate(**template_doc)

# ============== MEUS AGENDAMENTOS ==============

@api_router.get('/my-appointments')
async def get_my_appointments(
    date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Retorna os agendamentos do usuário atual.
    - Televendas/Comercial: agendamentos que criou
    - Agente: agendamentos atribuídos a ele
    - Supervisor: agendamentos que criou OU atribuídos a ele
    """
    if current_user.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail='Administradores não têm acesso a esta funcionalidade')
    
    query = {}
    
    # Filtrar por data se fornecida
    if date:
        query['date'] = date
    
    # Para agentes: agendamentos atribuídos a eles
    if current_user.role == UserRole.AGENTE:
        query['user_id'] = current_user.id
    # Para televendas: agendamentos criados por eles
    elif current_user.role == UserRole.TELEVENDAS:
        query['created_by'] = current_user.id
    # Para supervisores: ambos (criados ou atribuídos)
    elif current_user.role == UserRole.SUPERVISOR:
        query['$or'] = [
            {'created_by': current_user.id},
            {'user_id': current_user.id}
        ]
    
    appointments = await db.appointments.find(query, {'_id': 0}).sort([('date', -1), ('time_slot', 1)]).to_list(500)
    
    # Adicionar informação do agente atribuído
    for apt in appointments:
        if apt.get('user_id'):
            agent = await db.users.find_one({'id': apt['user_id']}, {'_id': 0, 'name': 1})
            apt['agent_name'] = agent.get('name') if agent else 'Desconhecido'
        else:
            apt['agent_name'] = None
        
        # Verificar se há solicitação pendente para este agendamento
        pending_request = await db.change_requests.find_one({
            'appointment_id': apt['id'],
            'status': 'pending'
        }, {'_id': 0})
        apt['has_pending_request'] = pending_request is not None
        apt['pending_request'] = pending_request
    
    return appointments

@api_router.get('/my-appointments/stats')
async def get_my_appointments_stats(
    current_user: User = Depends(get_current_user)
):
    """Retorna estatísticas dos meus agendamentos"""
    if current_user.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail='Administradores não têm acesso a esta funcionalidade')
    
    # Montar query baseada no role
    if current_user.role == UserRole.AGENTE:
        base_query = {'user_id': current_user.id}
    elif current_user.role == UserRole.TELEVENDAS:
        base_query = {'created_by': current_user.id}
    else:  # Supervisor
        base_query = {'$or': [{'created_by': current_user.id}, {'user_id': current_user.id}]}
    
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    # Total
    total = await db.appointments.count_documents(base_query)
    
    # Hoje
    today_query = {**base_query, 'date': today} if '$or' not in base_query else {'$and': [base_query, {'date': today}]}
    today_count = await db.appointments.count_documents(today_query)
    
    # Pendentes
    pending_query = {**base_query, 'status': 'pendente_atribuicao'} if '$or' not in base_query else {'$and': [base_query, {'status': 'pendente_atribuicao'}]}
    pending = await db.appointments.count_documents(pending_query)
    
    # Emitidos
    emitidos_query = {**base_query, 'status': 'emitido'} if '$or' not in base_query else {'$and': [base_query, {'status': 'emitido'}]}
    emitidos = await db.appointments.count_documents(emitidos_query)
    
    # Solicitações pendentes de aprovação (apenas para supervisor)
    pending_requests = 0
    if current_user.role == UserRole.SUPERVISOR:
        pending_requests = await db.change_requests.count_documents({'status': 'pending'})
    
    return {
        'total': total,
        'today': today_count,
        'pending': pending,
        'emitidos': emitidos,
        'pending_requests': pending_requests
    }

# ============== SOLICITAÇÕES DE ALTERAÇÃO ==============

@api_router.post('/change-requests')
async def create_change_request(
    request: ChangeRequestCreate,
    current_user: User = Depends(get_current_user)
):
    """Criar solicitação de edição ou cancelamento de agendamento"""
    # Buscar agendamento
    apt = await db.appointments.find_one({'id': request.appointment_id}, {'_id': 0})
    if not apt:
        raise HTTPException(status_code=404, detail='Agendamento não encontrado')
    
    # Verificar se não é emitido
    if apt.get('status') == 'emitido':
        raise HTTPException(status_code=400, detail='Não é possível editar ou cancelar agendamentos já emitidos')
    
    # Verificar se o usuário tem permissão (criou ou é atribuído)
    is_creator = apt.get('created_by') == current_user.id
    is_assigned = apt.get('user_id') == current_user.id
    is_supervisor = current_user.role == UserRole.SUPERVISOR
    
    if not (is_creator or is_assigned or is_supervisor):
        raise HTTPException(status_code=403, detail='Você não tem permissão para modificar este agendamento')
    
    # Se for supervisor, aplicar diretamente
    if is_supervisor:
        now_str = datetime.now(timezone.utc).isoformat()
        
        if request.request_type == 'cancel':
            # Cancelar diretamente
            await db.appointments.update_one(
                {'id': request.appointment_id},
                {'$set': {'status': 'cancelado', 'updated_at': now_str}}
            )
            # Registrar no histórico
            await db.appointment_history.insert_one({
                'id': str(uuid.uuid4()),
                'appointment_id': request.appointment_id,
                'user_id': current_user.id,
                'user_name': current_user.name,
                'timestamp': now_str,
                'changes': [{'field': 'status', 'old': apt.get('status'), 'new': 'cancelado', 'reason': request.reason or 'Cancelado pelo supervisor'}]
            })
            return {'message': 'Agendamento cancelado com sucesso', 'status': 'approved'}
        else:
            # Editar diretamente
            updates = {'updated_at': now_str}
            changes = []
            
            if request.new_first_name:
                changes.append({'field': 'first_name', 'old': apt.get('first_name'), 'new': request.new_first_name})
                updates['first_name'] = request.new_first_name
            if request.new_last_name:
                changes.append({'field': 'last_name', 'old': apt.get('last_name'), 'new': request.new_last_name})
                updates['last_name'] = request.new_last_name
            if request.new_protocol_number:
                changes.append({'field': 'protocol_number', 'old': apt.get('protocol_number'), 'new': request.new_protocol_number})
                updates['protocol_number'] = request.new_protocol_number
            if request.new_additional_protocols is not None:
                changes.append({'field': 'additional_protocols', 'old': apt.get('additional_protocols', []), 'new': request.new_additional_protocols})
                updates['additional_protocols'] = request.new_additional_protocols
            if request.new_date:
                changes.append({'field': 'date', 'old': apt.get('date'), 'new': request.new_date})
                updates['date'] = request.new_date
            if request.new_time_slot:
                changes.append({'field': 'time_slot', 'old': apt.get('time_slot'), 'new': request.new_time_slot})
                updates['time_slot'] = request.new_time_slot
            if request.new_notes is not None:
                changes.append({'field': 'notes', 'old': apt.get('notes'), 'new': request.new_notes})
                updates['notes'] = request.new_notes
            
            if changes:
                await db.appointments.update_one({'id': request.appointment_id}, {'$set': updates})
                await db.appointment_history.insert_one({
                    'id': str(uuid.uuid4()),
                    'appointment_id': request.appointment_id,
                    'user_id': current_user.id,
                    'user_name': current_user.name,
                    'timestamp': now_str,
                    'changes': changes
                })
            
            return {'message': 'Agendamento atualizado com sucesso', 'status': 'approved'}
    
    # Verificar se já existe solicitação pendente
    existing = await db.change_requests.find_one({
        'appointment_id': request.appointment_id,
        'status': 'pending'
    })
    if existing:
        raise HTTPException(status_code=400, detail='Já existe uma solicitação pendente para este agendamento')
    
    # Verificar se está próximo do horário (auto-aprovar se < 30 minutos)
    apt_datetime_str = f"{apt['date']}T{apt['time_slot']}:00"
    apt_datetime = datetime.fromisoformat(apt_datetime_str).replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    time_until = (apt_datetime - now).total_seconds() / 60  # minutos
    
    auto_approve = time_until <= 30 and time_until > 0
    
    now_str = now.isoformat()
    request_id = str(uuid.uuid4())
    
    request_doc = {
        'id': request_id,
        'appointment_id': request.appointment_id,
        'request_type': request.request_type,
        'status': 'auto_approved' if auto_approve else 'pending',
        'reason': request.reason,
        'new_first_name': request.new_first_name,
        'new_last_name': request.new_last_name,
        'new_protocol_number': request.new_protocol_number,
        'new_additional_protocols': request.new_additional_protocols,
        'new_date': request.new_date,
        'new_time_slot': request.new_time_slot,
        'new_notes': request.new_notes,
        'requested_by': current_user.id,
        'requested_by_name': current_user.name,
        'created_at': now_str,
        'reviewed_by': 'system' if auto_approve else None,
        'reviewed_at': now_str if auto_approve else None,
        'review_notes': 'Auto-aprovado por proximidade do horário' if auto_approve else None
    }
    
    await db.change_requests.insert_one(request_doc)
    
    # Se auto-aprovado, aplicar a mudança
    if auto_approve:
        if request.request_type == 'cancel':
            await db.appointments.update_one(
                {'id': request.appointment_id},
                {'$set': {'status': 'cancelado', 'updated_at': now_str}}
            )
        else:
            updates = {'updated_at': now_str}
            if request.new_first_name:
                updates['first_name'] = request.new_first_name
            if request.new_last_name:
                updates['last_name'] = request.new_last_name
            if request.new_protocol_number:
                updates['protocol_number'] = request.new_protocol_number
            if request.new_additional_protocols is not None:
                updates['additional_protocols'] = request.new_additional_protocols
            if request.new_date:
                updates['date'] = request.new_date
            if request.new_time_slot:
                updates['time_slot'] = request.new_time_slot
            if request.new_notes is not None:
                updates['notes'] = request.new_notes
            await db.appointments.update_one({'id': request.appointment_id}, {'$set': updates})
        
        return {
            'message': 'Solicitação auto-aprovada por proximidade do horário',
            'status': 'auto_approved',
            'request': ChangeRequestResponse(**request_doc)
        }
    
    # Criar notificação para supervisores
    supervisors = await db.users.find({'role': UserRole.SUPERVISOR, 'approved': True}, {'_id': 0, 'id': 1}).to_list(100)
    for sup in supervisors:
        await db.notifications.insert_one({
            'id': str(uuid.uuid4()),
            'user_id': sup['id'],
            'type': 'change_request_pending',
            'message': f'{current_user.name} solicitou {"cancelamento" if request.request_type == "cancel" else "edição"} do agendamento de {apt["first_name"]} {apt["last_name"]}',
            'read': False,
            'created_at': now_str
        })
    
    return {
        'message': 'Solicitação criada e aguardando aprovação do supervisor',
        'status': 'pending',
        'request': ChangeRequestResponse(**request_doc)
    }

@api_router.get('/change-requests')
async def list_change_requests(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Listar solicitações de alteração"""
    query = {}
    
    # Supervisores veem todas, outros veem apenas as suas
    if current_user.role != UserRole.SUPERVISOR:
        query['requested_by'] = current_user.id
    
    if status:
        query['status'] = status
    
    requests = await db.change_requests.find(query, {'_id': 0}).sort('created_at', -1).to_list(200)
    
    # Adicionar informações do agendamento
    for req in requests:
        apt = await db.appointments.find_one({'id': req['appointment_id']}, {'_id': 0, 'first_name': 1, 'last_name': 1, 'date': 1, 'time_slot': 1, 'status': 1})
        if apt:
            req['appointment'] = apt
    
    return requests

@api_router.put('/change-requests/{request_id}/review')
async def review_change_request(
    request_id: str,
    approved: bool,
    review_notes: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Aprovar ou rejeitar uma solicitação de alteração (apenas supervisor)"""
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail='Apenas supervisores podem aprovar solicitações')
    
    request_doc = await db.change_requests.find_one({'id': request_id}, {'_id': 0})
    if not request_doc:
        raise HTTPException(status_code=404, detail='Solicitação não encontrada')
    
    if request_doc['status'] != 'pending':
        raise HTTPException(status_code=400, detail='Esta solicitação já foi processada')
    
    now_str = datetime.now(timezone.utc).isoformat()
    new_status = 'approved' if approved else 'rejected'
    
    # Atualizar a solicitação
    await db.change_requests.update_one(
        {'id': request_id},
        {'$set': {
            'status': new_status,
            'reviewed_by': current_user.id,
            'reviewed_at': now_str,
            'review_notes': review_notes
        }}
    )
    
    # Se aprovado, aplicar a mudança
    if approved:
        apt = await db.appointments.find_one({'id': request_doc['appointment_id']}, {'_id': 0})
        
        if request_doc['request_type'] == 'cancel':
            await db.appointments.update_one(
                {'id': request_doc['appointment_id']},
                {'$set': {'status': 'cancelado', 'updated_at': now_str}}
            )
            # Registrar no histórico
            await db.appointment_history.insert_one({
                'id': str(uuid.uuid4()),
                'appointment_id': request_doc['appointment_id'],
                'user_id': current_user.id,
                'user_name': current_user.name,
                'timestamp': now_str,
                'changes': [{'field': 'status', 'old': apt.get('status') if apt else 'unknown', 'new': 'cancelado', 'reason': f'Aprovado por {current_user.name}'}]
            })
        else:
            updates = {'updated_at': now_str}
            changes = []
            
            if request_doc.get('new_first_name'):
                updates['first_name'] = request_doc['new_first_name']
                changes.append({'field': 'first_name', 'old': apt.get('first_name') if apt else None, 'new': request_doc['new_first_name']})
            if request_doc.get('new_last_name'):
                updates['last_name'] = request_doc['new_last_name']
                changes.append({'field': 'last_name', 'old': apt.get('last_name') if apt else None, 'new': request_doc['new_last_name']})
            if request_doc.get('new_protocol_number'):
                updates['protocol_number'] = request_doc['new_protocol_number']
                changes.append({'field': 'protocol_number', 'old': apt.get('protocol_number') if apt else None, 'new': request_doc['new_protocol_number']})
            if request_doc.get('new_additional_protocols') is not None:
                updates['additional_protocols'] = request_doc['new_additional_protocols']
                changes.append({'field': 'additional_protocols', 'old': apt.get('additional_protocols', []) if apt else [], 'new': request_doc['new_additional_protocols']})
            if request_doc.get('new_date'):
                updates['date'] = request_doc['new_date']
                changes.append({'field': 'date', 'old': apt.get('date') if apt else None, 'new': request_doc['new_date']})
            if request_doc.get('new_time_slot'):
                updates['time_slot'] = request_doc['new_time_slot']
                changes.append({'field': 'time_slot', 'old': apt.get('time_slot') if apt else None, 'new': request_doc['new_time_slot']})
            if request_doc.get('new_notes') is not None:
                updates['notes'] = request_doc['new_notes']
                changes.append({'field': 'notes', 'old': apt.get('notes') if apt else None, 'new': request_doc['new_notes']})
            
            await db.appointments.update_one({'id': request_doc['appointment_id']}, {'$set': updates})
            
            if changes:
                await db.appointment_history.insert_one({
                    'id': str(uuid.uuid4()),
                    'appointment_id': request_doc['appointment_id'],
                    'user_id': current_user.id,
                    'user_name': current_user.name,
                    'timestamp': now_str,
                    'changes': changes
                })
    
    # Notificar o solicitante
    status_text = 'aprovada' if approved else 'rejeitada'
    await db.notifications.insert_one({
        'id': str(uuid.uuid4()),
        'user_id': request_doc['requested_by'],
        'type': 'change_request_reviewed',
        'message': f'Sua solicitação de {"cancelamento" if request_doc["request_type"] == "cancel" else "edição"} foi {status_text}',
        'read': False,
        'created_at': now_str
    })
    
    return {'message': f'Solicitação {status_text}', 'status': new_status}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=['*'],
    allow_headers=['*'],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event('shutdown')
async def shutdown_db_client():
    global auto_assign_task, presence_check_task
    if auto_assign_task:
        auto_assign_task.cancel()
    if presence_check_task:
        presence_check_task.cancel()
    client.close()

# ============== AUTO-ASSIGN SYSTEM ==============

async def get_next_agent_round_robin(date: str, time_slot: str, prefer_online: bool = True):
    """Seleciona o próximo agente usando distribuição round-robin equilibrada"""
    now = datetime.now(timezone.utc)
    
    agents = await db.users.find({
        'role': UserRole.AGENTE, 
        'approved': True
    }, {'_id': 0}).to_list(100)
    
    if not agents:
        return None
    
    # Contar agendamentos do dia para cada agente
    agent_loads = []
    for agent in agents:
        # Verificar se já tem agendamento neste horário específico
        conflict = await db.appointments.find_one({
            'user_id': agent['id'],
            'date': date,
            'time_slot': time_slot,
            'status': {'$ne': 'cancelado'}
        })
        
        if conflict:
            continue  # Pular agentes com conflito de horário
        
        # Verificar status online
        is_online = agent.get('is_online', False)
        last_seen = agent.get('last_seen')
        
        if last_seen and is_online:
            last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
            minutes_ago = (now - last_seen_dt).total_seconds() / 60
            if minutes_ago > PRESENCE_TIMEOUT_MINUTES:
                is_online = False
        
        # Contar total de agendamentos no dia
        day_count = await db.appointments.count_documents({
            'user_id': agent['id'],
            'date': date,
            'status': {'$ne': 'cancelado'}
        })
        
        agent_loads.append({
            'agent': agent,
            'load': day_count,
            'is_online': is_online
        })
    
    if not agent_loads:
        return None
    
    # Priorizar agentes online se prefer_online=True
    if prefer_online:
        online_agents = [a for a in agent_loads if a['is_online']]
        if online_agents:
            agent_loads = online_agents
    
    # Ordenar por carga (menos ocupado primeiro) para distribuição equilibrada
    agent_loads.sort(key=lambda x: x['load'])
    return agent_loads[0]['agent']

async def auto_assign_pending_appointments():
    """Atribui automaticamente agendamentos pendentes há mais de 5 minutos"""
    while True:
        try:
            await asyncio.sleep(60)  # Verificar a cada 1 minuto
            
            now = datetime.now(timezone.utc)
            cutoff_time = now - timedelta(minutes=AUTO_ASSIGN_MINUTES)
            
            # Buscar agendamentos pendentes há mais de 5 minutos
            pending = await db.appointments.find({
                'status': 'pendente_atribuicao',
                'reserved_at': {'$lt': cutoff_time.isoformat()}
            }, {'_id': 0}).to_list(100)
            
            for apt in pending:
                agent = await get_next_agent_round_robin(apt['date'], apt['time_slot'])
                
                if agent:
                    # ...existing code for auto-assign...
                    await db.appointments.update_one(
                        {'id': apt['id']},
                        {'$set': {
                            'user_id': agent['id'],
                            'status': 'confirmado',
                            'updated_at': now.isoformat(),
                            'auto_assigned': True
                        }}
                    )
                    await db.notifications.delete_many({
                        'appointment_id': apt['id'],
                        'type': 'pending_assignment'
                    })
                    notif_doc = {
                        'id': str(uuid.uuid4()),
                        'user_id': agent['id'],
                        'appointment_id': apt['id'],
                        'message': f'Agendamento atribuído automaticamente: {apt["first_name"]} {apt["last_name"]}',
                        'type': 'auto_assigned',
                        'read': False,
                        'created_at': now.isoformat()
                    }
                    await db.notifications.insert_one(notif_doc)
                    supervisors = await db.users.find({'role': UserRole.SUPERVISOR}, {'_id': 0}).to_list(100)
                    for sup in supervisors:
                        sup_notif = {
                            'id': str(uuid.uuid4()),
                            'user_id': sup['id'],
                            'appointment_id': apt['id'],
                            'message': f'Agendamento de {apt["first_name"]} {apt["last_name"]} foi atribuído automaticamente a {agent["name"]}',
                            'type': 'auto_assigned_info',
                            'read': False,
                            'created_at': now.isoformat()
                        }
                        await db.notifications.insert_one(sup_notif)
                    logger.info(f'Auto-assigned appointment {apt["id"]} to agent {agent["name"]}')
                else:
                    # Verificação de situação crítica para alerta supervisor
                    # 1. Já está pendente há mais de 10 minutos
                    # 2. Faltam menos de 10 minutos para o horário agendado
                    # 3. Horário agendado já chegou ou passou
                    # E não enviar duplicado
                    supervisor_alert_sent = apt.get('supervisor_alert_sent', False)
                    if not supervisor_alert_sent:
                        reserved_at = apt.get('reserved_at')
                        date_str = apt.get('date')
                        time_slot = apt.get('time_slot')
                        # Calcular tempos
                        try:
                            reserved_dt = datetime.fromisoformat(reserved_at.replace('Z', '+00:00')) if reserved_at else None
                            apt_dt = datetime.fromisoformat(f"{date_str}T{time_slot}:00+00:00") if date_str and time_slot else None
                        except Exception:
                            reserved_dt = None
                            apt_dt = None
                        critical = False
                        if reserved_dt and (now - reserved_dt).total_seconds() > 600:
                            critical = True
                        if apt_dt:
                            minutes_to_apt = (apt_dt - now).total_seconds() / 60
                            if minutes_to_apt < 10:
                                critical = True
                            if now >= apt_dt:
                                critical = True
                        if critical:
                            # Notificar todos supervisores
                            supervisors = await db.users.find({'role': UserRole.SUPERVISOR}, {'_id': 0}).to_list(100)
                            for sup in supervisors:
                                notif = {
                                    'id': str(uuid.uuid4()),
                                    'user_id': sup['id'],
                                    'appointment_id': apt['id'],
                                    'message': f'Agendamento de {apt["first_name"]} {apt["last_name"]} está pendente e em situação crítica (sem agente disponível).',
                                    'type': 'supervisor_critical_pending',
                                    'read': False,
                                    'created_at': now.isoformat()
                                }
                                await db.notifications.insert_one(notif)
                            # Marcar alerta enviado
                            await db.appointments.update_one(
                                {'id': apt['id']},
                                {'$set': {'supervisor_alert_sent': True}}
                            )
        except asyncio.CancelledError:
            logger.info('Auto-assign task cancelled')
            break
        except Exception as e:
            logger.error(f'Error in auto-assign task: {e}')
            await asyncio.sleep(60)

@app.on_event('startup')
async def startup_event():
    global auto_assign_task, presence_check_task
    auto_assign_task = asyncio.create_task(auto_assign_pending_appointments())
    presence_check_task = asyncio.create_task(check_presence_and_redistribute())
    logger.info('Auto-assign background task started')
    logger.info('Presence check background task started')

async def check_presence_and_redistribute():
    """Verifica presença dos agentes e redistribui agendamentos de ausentes"""
    while True:
        try:
            await asyncio.sleep(120)  # Verificar a cada 2 minutos
            
            now = datetime.now(timezone.utc)
            today = now.date().isoformat()
            cutoff = now - timedelta(minutes=PRESENCE_TIMEOUT_MINUTES)
            
            # Buscar agentes que ficaram offline
            agents = await db.users.find({
                'role': UserRole.AGENTE,
                'approved': True,
                'is_online': True
            }, {'_id': 0}).to_list(100)
            
            for agent in agents:
                last_seen = agent.get('last_seen')
                if not last_seen:
                    continue
                
                last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                
                if last_seen_dt < cutoff:
                    # Agente ficou offline - marcar como offline
                    await db.users.update_one(
                        {'id': agent['id']},
                        {'$set': {'is_online': False}}
                    )
                    
                    logger.info(f'Agent {agent["name"]} marked as offline (no heartbeat)')
                    
                    # Buscar agendamentos futuros do agente que podem ser redistribuídos
                    current_time = now.strftime('%H:%M')
                    upcoming_appointments = await db.appointments.find({
                        'user_id': agent['id'],
                        'date': today,
                        'time_slot': {'$gt': current_time},
                        'status': 'confirmado'
                    }, {'_id': 0}).to_list(100)
                    
                    # Redistribuir para agentes online
                    for apt in upcoming_appointments:
                        new_agent = await get_next_agent_round_robin(apt['date'], apt['time_slot'], prefer_online=True)
                        
                        if new_agent and new_agent['id'] != agent['id']:
                            # Redistribuir
                            await db.appointments.update_one(
                                {'id': apt['id']},
                                {'$set': {
                                    'user_id': new_agent['id'],
                                    'updated_at': now.isoformat(),
                                    'redistributed': True,
                                    'redistributed_from': agent['id']
                                }}
                            )
                            
                            # Notificar novo agente
                            notif = {
                                'id': str(uuid.uuid4()),
                                'user_id': new_agent['id'],
                                'appointment_id': apt['id'],
                                'message': f'Agendamento redistribuído de {agent["name"]}: {apt["first_name"]} {apt["last_name"]} às {apt["time_slot"]}',
                                'type': 'redistributed',
                                'read': False,
                                'created_at': now.isoformat()
                            }
                            await db.notifications.insert_one(notif)
                            
                            # Notificar supervisores
                            supervisors = await db.users.find({'role': UserRole.SUPERVISOR}, {'_id': 0}).to_list(100)
                            for sup in supervisors:
                                sup_notif = {
                                    'id': str(uuid.uuid4()),
                                    'user_id': sup['id'],
                                    'appointment_id': apt['id'],
                                    'message': f'Agendamento de {apt["first_name"]} {apt["last_name"]} redistribuído de {agent["name"]} para {new_agent["name"]} (agente ausente)',
                                    'type': 'redistributed_info',
                                    'read': False,
                                    'created_at': now.isoformat()
                                }
                                await db.notifications.insert_one(sup_notif)
                            
                            logger.info(f'Redistributed appointment {apt["id"]} from {agent["name"]} to {new_agent["name"]}')
                    
        except asyncio.CancelledError:
            logger.info('Presence check task cancelled')
            break
        except Exception as e:
            logger.error(f'Error in presence check task: {e}')
            await asyncio.sleep(120)
