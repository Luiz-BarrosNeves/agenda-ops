"""
AgendaHub Backend Server - Versão Completa e Corrigida
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
    chat_platform: Optional[strO erro continua no arquivo `server.py`: **SyntaxError na linha 135** por causa de de artefato de edição.
A linha está cortada: `first_name: Optional[str```python`.

**Corrige no teu server.py agora:**

Abre o arquivo e garante que a linha 135 termina assim:
```python
first_name: Optional[str] = None
