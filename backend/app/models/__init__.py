from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional

# ==================== USER MODELS ====================

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

class UserApprove(BaseModel):
    approved: bool

class UserUpdateRole(BaseModel):
    role: str

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
    is_online: Optional[bool] = False
    last_seen: Optional[str] = None
    created_at: str

# ==================== APPOINTMENT MODELS ====================

class AppointmentCreate(BaseModel):
    first_name: str
    last_name: str
    protocol_number: str
    additional_protocols: Optional[List[str]] = []
    has_chat: bool = False
    date: str
    time_slot: str
    notes: Optional[str] = None
    reschedule_reason: Optional[str] = None  # Motivo do reagendamento (padronizado)

class AppointmentAssign(BaseModel):
    user_id: str

class AppointmentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    protocol_number: Optional[str] = None
    additional_protocols: Optional[List[str]] = None
    has_chat: Optional[bool] = None
    date: Optional[str] = None
    time_slot: Optional[str] = None
    appointment_type: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    reschedule_reason: Optional[str] = None  # Motivo do reagendamento (padronizado)

class Appointment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    first_name: str
    last_name: str
    protocol_number: str
    additional_protocols: List[str] = []
    has_chat: bool
    date: str
    time_slot: str
    appointment_type: str
    status: str
    notes: Optional[str] = None
    reschedule_reason: Optional[str] = None  # Motivo do reagendamento (padronizado)
    documents: List[str] = []
    user_id: Optional[str] = None
    agent_name: Optional[str] = None  # Nome do agente atribuído
    assigned_by: Optional[str] = None
    assigned_at: Optional[str] = None
    auto_assigned: bool = False
    supervisor_alert_sent: bool = False
    created_by: str
    created_at: str
    updated_at: str

# ==================== SLOT MODELS ====================

class SlotAvailability(BaseModel):
    time_slot: str
    total: int
    available: int
    occupied: int
    is_extra: bool = False

class ExtraHoursUpdate(BaseModel):
    times: List[str]

# ==================== NOTIFICATION MODELS ====================

class Notification(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    message: str
    type: str
    read: bool
    created_at: str

# ==================== FILTER MODELS ====================

class AppointmentFilters(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    client_name: Optional[str] = None
