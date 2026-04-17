"""
AgendaHub Backend Server
========================
Ponto de entrada principal corrigido e consolidado.
"""

import os
import logging
import shutil
import asyncio
import csv
import io
import uuid
import jwt
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import List, Optional

from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, StreamingResponse
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from passlib.hash import bcrypt

# --- Configuração Inicial ---
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

UPLOAD_DIR = ROOT_DIR / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)

# Database
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'agenda_hub')]

# Timezone
BR_TZ = ZoneInfo("America/Sao_Paulo")

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Segurança e Auth ---
security = HTTPBearer()

# Configurações JWT
try:
    from app.config import JWT_SECRET, JWT_ALGORITHM
except ImportError:
    # Fallback para desenvolvimento se app.config não existir
    JWT_SECRET = os.environ.get('JWT_SECRET', 'dev_secret_key_change_in_prod')
    JWT_ALGORITHM = os.environ.get('JWT_ALGORITHM', 'HS256')

# Constantes de Negócio
AUTO_ASSIGN_MINUTES = 5
PRESENCE_TIMEOUT_MINUTES = 3
EXTRA_TIME_SLOTS = ['07:40', '12:40', '18:00', '18:20', '18:40']

# Variáveis Globais de Task
auto_assign_task = None
presence_check_task = None

# --- Definição de Roles ---
class UserRole:
    ADMIN = 'admin'
    SUPERVISOR = 'supervisor'
    AGENTE = 'agente'
    TELEVENDAS = 'televendas'
    COMERCIAL = 'comercial'

# --- Pydantic Models ---
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
    chat_platform: Optional[str] = None
    date: str
    time_slot: str
    notes: Optional[str] = None
    emission_system: Optional[str] = None
    reschedule_reason: Optional[str] = None

class AppointmentAssign(BaseModel):
    user_id: str

class AppointmentUpdate(BaseModel):
    first_name: Optional[str```python
"""
AgendaHub Backend Server - Arquivo único para copiar e colar.
================ar.
========================
Ponto de entrada principal corrigido. Removeu duplicidade de CORS.
Configs: JWT, MongoDB, Timezone America/Sao_Paulo.
Para rodar: pip install fastapi uvicorn python-dotenv passlib[bcrypt] pymongo motor boto3 pytest
"""

import os
import logging
import shutil
import asyncio
import csv
import io
import uuid
import jwt
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import List, Optional
from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, StreamingResponse
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from passlib.hash import bcrypt

# === Configuração Inicial ===
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

UPLOAD_DIR = ROOT_DIR / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

security = HTTPBearer()
logger = logging.getLogger(__name__)
BR_TZ = ZoneInfo("America/Sao_Paulo")

# === JWT Config ===
from app.config import JWT_SECRET, JWT_ALGORITHM

# === Roles ===
class UserRole:
    ADMIN = 'admin'
    SUPERVISOR = 'supervisor'
    AGENTE = 'agente'
    TELEVENDAS = 'televendas'
    COMERCIAL = 'comercial'

# === Models ===
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str
    avatar_url: Optional[str] = None
    approved: bool = False
    can_safeweb: bool = False
    can_serpro: bool = False

class UserApprove(BaseModel): approved: bool
class UserUpdateRole(BaseModel): role: str
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
    chat_platform: Optional[str] = None
    date: str
    time_slot: str
    notes: Optional[str] = None
    emission_system: Optional[str] = None
    reschedule_reason: Optional[str] = None
class AppointmentAssign(BaseModel): user_id: str

class AppointmentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    protocol_number: Optional[str] = None
    additional_protocols: Optional[List[str]] = None
    has_chat: Optional[bool] = None
    chat_platform: Optional[str] = None
    date: Optional[str] = None
    time_slot: Optional[str] = None
    appointment_type: Optional[str] = None
    status: Optional[str]```python
"""
AgendaHub Backend Server v2 - Código completo pronto pra copiar-colar
"""

import os
import logging
import shutil
import asyncio
import csv
import io
import uuid
import jwt
from pathlib import Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import List, Optional

# ------------------- FASTAPI CORE -------------------
from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Query, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, StreamingResponse
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from passlib.hash import bcrypt

# ------------------- INITS -------------------
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

UPLOAD_DIR = ROOT_DIR / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

BR_TZ = ZoneInfo("America/Sao_Paulo")
security = HTTPBearer()

app = FastAPI(title="AgendaHub Backend", version="2.0")

# CORS - SUBSTITUÍDO PELO FIXO ABAIXO
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://agenda-ops.vercel.app",
        "https://agenda-ops-git-main-luiz-neves-projects.vercel.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ------------------- JWT/SECRET -------------------
from app.config import JWT_SECRET, JWT_ALGORITHM

# ------------------- CORE UTILS -------------------
async def centralized_get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    payload = jwt.decode(token, JWT_SECRET, algorithms=)
    user_id = payload.get('user_id')
    if not user_id: raise HTTPException(status_code=401, detail='Invalid token')
    user = await db.users.find_one({'id': user_id}, {'_id': 0})
    if not user: raise HTTPException(status_code=401, detail='User not found')
    return User(**user)

def check_role_permission(current_user, allowed_roles, action='realizar esta ação'):
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail=f'Usuário do perfil {current_user.role} não pode {action}')

def block_admin(current_user):
    if current_user.role == 'admin':
        raise HTTPException(status_code=403, detail='Usuário ADMIN não pode realizar esta ação')

def block_agent(current_user):
    if current_user.role == 'agente':
        raise HTTPException(status_code=403, detail='Usuário AGENTE não pode realizar esta ação')

def validate_agent_update_fields(update_data, apt, current_user):
    allowed_fields = {'date', 'time_slot'}
    for field in update_data:
        if field not in allowed_fields:
            raise HTTPException(status_code=403, detail='AGENTE só pode alterar data e horário do próprio agendamento')
    if apt.get('user_id') != current_user.id:
        raise HTTPException(status_code=403, detail='AGENTE só pode editar o próprio agendamento')

def validate_no_agent_assignment(update_data, current_user):
    agent_fields = {'user_id', 'user_name', 'new_agent_id', 'new_agent_name', 'available_agent'}
    for field in update_data:
        if field in agent_fields:
            raise HTTPException(status_code=403, detail='Você não tem permissão para designar ou alterar agente')

# ------------------- PYDANTIC MODELS -------------------
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

class User(AppModel):
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
    chat_platform: Optional[str] = None
    date: str
    time_slot: str
    notes: Optional[str] = None
    emission_system: Optional[str] = None
    reschedule_reason: Optional[str] = None

class Appointment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: Optional[str] = None
    first_name: str
    last_name: str
    protocol_number: str
    additional_protocols: List[str] = []
    has_chat: bool
    chat_platform: Optional[str] = None
    date: str
    time_slot: str
    appointment_type: str
    status: str
    notes: Optional[str] = None

# ------------------- ROUTERS -------------------
api_router = APIRouter(prefix="/api")

@api_router.post('/auth/register', response_model=User)
async def register(user_data: UserCreate):
    existing = await db.users.find_one({'email': user_data.email})
    if existing: raise HTTPException(status_code=400, detail='Email already registered')

    user_id = str(uuid.uuid4())
    hashed_password = bcrypt.hash(user_data.password)

    approved = user_data.role in ['supervisor', 'admin']

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
        supervisors = await db.users.find({'role': 'supervisor'}, {'_id': 0}).to_list(100)
        for sup in supervisors:
            notif_doc = {
                'id': str(uuid.uuid4()),
                'user_id': sup['id'],
                'message': f'Novo usuário pendente de aprovação: {user_data.name}',
                'type': 'user_approval_pending',
                'read': False,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            await db.notifications.insert_one(notif_doc)

    return User(**user_doc)

@api_router.post('/auth/login')
async def login(credentials: UserLogin):
    user = await db.users.find_one({'email': credentials.email})
    if not user or not bcrypt.verify(credentials.password, user['password_hash']):
        raise HTTPException(status_code=401, detail='Invalid credentials')
    if not user.get('approved'): raise HTTPException(status_code=403, detail='Aguardando aprovação')

    payload = {'user_id': user['id'], 'exp': datetime.now(timezone.utc)+timedelta(days=7)}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {'token': token, 'user': User(**user)}

@api_router.get('/auth/me', response_model=User)
async def get_me(current_user: User = Depends(centralized_get_current_user)):
    return current_user

@api_router.get('/appointments', response_model=List)
async def get_appointments(date: Optional[str]=None,
                          status: Optional[str]=None,
                          current_user: User = Depends(centralized_get_current_user)):
    query = {'user_id': current_user.id} if current_user.role == 'agente' else {}
    if date: query['date'] = date
    if status: query['status'] = status
    apps = await db.appointments.find(query, {'_id':0}).to_list(500)
    return [Appointment(**a) for a in apps]

api_router.include_router(router)
app.include_router(api_router)

# ------------------- STARTUP -------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
