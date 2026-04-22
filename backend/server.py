import os
import uuid
import shutil
import logging
import jwt 
import csv

from io import StringIO
from zoneinfo import ZoneInfo
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, Response
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, ConfigDict
from passlib.hash import bcrypt

print("SERVER.PY FOI CARREGADO")

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME")
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET não definida")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "").split(",") if origin.strip()]

if not MONGO_URL:
    raise RuntimeError("MONGO_URL não definida")
if not DB_NAME:
    raise RuntimeError("DB_NAME não definida")

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
security = HTTPBearer()

app = FastAPI(title="AgendaOps API")

ALLOWED_ORIGINS = [
    "https://agenda-ops.vercel.app",
    "https://agenda-ops-git-main-luiz-neves-projects.vercel.app",
    "http://localhost:3000",
]

print("ALLOWED_ORIGINS:", ALLOWED_ORIGINS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.options("/{full_path:path}")
async def preflight_handler(full_path: str):
    return Response(status_code=204)

api_router = APIRouter(prefix="/api")


class UserRole:
    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    AGENTE = "agente"
    TELEVENDAS = "televendas"
    COMERCIAL = "comercial"


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str
    avatar_url: Optional[str] = None
    approved: bool = False
    can_safeweb: bool = False
    can_serpro: bool = False


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdateRole(BaseModel):
    role: str


class UserUpdatePermissions(BaseModel):
    can_safeweb: Optional[bool] = None
    can_serpro: Optional[bool] = None


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
    additional_protocols: List[str] = []
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
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    protocol_number: Optional[str] = None
    additional_protocols: Optional[List[str]] = None
    has_chat: Optional[bool] = None
    chat_platform: Optional[str] = None
    date: Optional[str] = None
    time_slot: Optional[str] = None
    appointment_type: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    emission_system: Optional[str] = None
    reschedule_reason: Optional[str] = None


class Appointment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: Optional[str] = None
    agent_name: Optional[str] = None
    first_name: str
    last_name: str
    protocol_number: str
    additional_protocols: List[str] = []
    has_chat: bool = False
    chat_platform: Optional[str] = None
    document_urls: List[str] = []
    date: str
    time_slot: str
    occupies_two_slots: bool = False
    appointment_type: str
    status: str
    notes: Optional[str] = None
    emission_system: Optional[str] = None
    created_by: str
    created_at: str
    updated_at: str
    reserved_at: str
    reschedule_reason: Optional[str] = None


class Notification(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    message: str
    type: str
    read: bool
    created_at: str


class HealthResponse(BaseModel):
    status: str
    service: str
    db_name: str


def check_role_permission(current_user: User, allowed_roles: List[str], action: str = "realizar esta ação") -> None:
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail=f"Usuário do perfil {current_user.role} não pode {action}")


def block_admin(current_user: User) -> None:
    if current_user.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Usuário ADMIN não pode realizar esta ação")


def block_agent(current_user: User) -> None:
    if current_user.role == UserRole.AGENTE:
        raise HTTPException(status_code=403, detail="Usuário AGENTE não pode realizar esta ação")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    token = credentials.credentials if credentials else None
    if not token:
        raise HTTPException(status_code=401, detail="Token ausente")

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return User(**user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("[AUTH ERROR] %s: %s", type(e).__name__, str(e))
        raise HTTPException(status_code=401, detail="Invalid token")


async def log_appointment_history(
    appointment_id: str,
    action: str,
    changed_by: str,
    changed_by_name: str,
    field_changed: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
) -> None:
    await db.appointment_history.insert_one(
        {
            "id": str(uuid.uuid4()),
            "appointment_id": appointment_id,
            "action": action,
            "field_changed": field_changed,
            "old_value": old_value,
            "new_value": new_value,
            "changed_by": changed_by,
            "changed_by_name": changed_by_name,
            "changed_at": datetime.now(timezone.utc).isoformat(),
        }
    )


@api_router.get("/health", response_model=HealthResponse)
async def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok", service="AgendaOps API", db_name=DB_NAME)


@api_router.post("/auth/register", response_model=User)
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_id = str(uuid.uuid4())
    approved = user_data.role in [UserRole.SUPERVISOR, UserRole.ADMIN]
    user_doc = {
        "id": user_id,
        "email": user_data.email,
        "password_hash": bcrypt.hash(user_data.password),
        "name": user_data.name,
        "role": user_data.role,
        "approved": approved,
        "avatar_url": user_data.avatar_url,
        "can_safeweb": user_data.can_safeweb,
        "can_serpro": user_data.can_serpro,
        "is_online": False,
        "last_seen": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user_doc)

    if not approved:
        supervisors = await db.users.find({"role": UserRole.SUPERVISOR}, {"_id": 0}).to_list(100)
        for supervisor in supervisors:
            await db.notifications.insert_one(
                {
                    "id": str(uuid.uuid4()),
                    "user_id": supervisor["id"],
                    "message": f"Novo usuário pendente de aprovação: {user_data.name} ({user_data.email})",
                    "type": "user_approval_pending",
                    "read": False,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    return User(**user_doc)


@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email}, {"_id": 0})
    if not user or not bcrypt.verify(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.get("approved", False):
        raise HTTPException(status_code=403, detail="Conta aguardando aprovação do supervisor")

    payload = {
        "user_id": user["id"],
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {"token": token, "user": User(**user)}


@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@api_router.get("/users", response_model=List[User])
async def get_users(pending_approval: Optional[bool] = None, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.SUPERVISOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Acesso não autorizado")

    query: Dict[str, Any] = {}
    if pending_approval is not None:
        query["approved"] = not pending_approval

    users = await db.users.find(query, {"_id": 0, "password_hash": 0}).to_list(200)
    return [User(**u) for u in users]


@api_router.post("/appointments", response_model=Appointment)
async def create_appointment(apt_data: AppointmentCreate, current_user: User = Depends(get_current_user)):
    block_admin(current_user)
    block_agent(current_user)
    check_role_permission(
        current_user,
        [UserRole.TELEVENDAS, UserRole.COMERCIAL, UserRole.SUPERVISOR],
        "criar agendamentos",
    )

    total_protocols = 1 + len(apt_data.additional_protocols)
    occupies_two_slots = total_protocols >= 3

    normal_time_slots = [
        "08:00", "08:20", "08:40",
        "09:00", "09:20", "09:40",
        "10:00", "10:20", "10:40",
        "11:00", "11:20", "11:40",
        "12:00", "12:20",
        "13:00", "13:20", "13:40",
        "14:00", "14:20", "14:40",
        "15:00", "15:20", "15:40",
        "16:00", "16:20", "16:40",
        "17:00", "17:20", "17:40",
    ]

    extra_hours_doc = await db.extra_hours.find_one({"date": apt_data.date}, {"_id": 0})
    extra_slots = extra_hours_doc.get("slots", []) if extra_hours_doc else []

    time_slots = sorted(set(normal_time_slots + extra_slots))

    if apt_data.time_slot not in time_slots:
        raise HTTPException(status_code=400, detail="Horário selecionado é inválido para esta data")

    if occupies_two_slots:
        current_index = time_slots.index(apt_data.time_slot)

    if current_index + 1 >= len(time_slots):
        raise HTTPException(
            status_code=400,
            detail="Este agendamento precisa de 2 horários consecutivos, mas não existe próximo horário disponível"
        )

    next_slot = time_slots[current_index + 1]

    agent_query = {"role": UserRole.AGENTE, "approved": True}
    if apt_data.emission_system:
        agent_query[f"can_{apt_data.emission_system}"] = True

    agents = await db.users.find(agent_query, {"_id": 0}).to_list(100)
    total_agents = len(agents)

    appointments = await db.appointments.find(
        {"date": apt_data.date, "status": {"$ne": "cancelado"}},
        {"_id": 0},
    ).to_list(1000)

    slot_index_map = {slot: idx for idx, slot in enumerate(time_slots)}

    def count_occupied(target_slot: str) -> int:
        slot_appointments = []

        for apt in appointments:
            apt_slot = apt.get("time_slot")
            if not apt_slot or apt_slot not in slot_index_map:
                continue

            occupies_two = apt.get("occupies_two_slots", False)
            apt_index = slot_index_map[apt_slot]
            current_slot_index = slot_index_map[target_slot]

            affects_current_slot = apt_index == current_slot_index

            if occupies_two and apt_index + 1 == current_slot_index:
                affects_current_slot = True

            if affects_current_slot:
                slot_appointments.append(apt)

        return len([
            a for a in slot_appointments
            if a.get("status") != "pendente_atribuicao"
        ])

    current_slot_occupied = count_occupied(apt_data.time_slot)
    next_slot_occupied = count_occupied(next_slot)

    if current_slot_occupied >= total_agents:
        raise HTTPException(
            status_code=400,
            detail="O horário selecionado não possui disponibilidade suficiente"
        )

    if next_slot_occupied >= total_agents:
        raise HTTPException(
            status_code=400,
            detail="Este agendamento precisa de 2 horários consecutivos, mas o próximo horário não está disponível"
        )

    emission_system = apt_data.emission_system
    if emission_system and emission_system not in ["safeweb", "serpro"]:
        raise HTTPException(status_code=400, detail="Sistema de emissão inválido")

    if apt_data.has_chat and apt_data.chat_platform not in ["blip", "chatpro"]:
        raise HTTPException(status_code=400, detail="Quando o cliente tem chat, é obrigatório selecionar a plataforma")

    now_str = datetime.now(timezone.utc).isoformat()
    apt_doc = {
        "id": str(uuid.uuid4()),
        "user_id": None,
        "first_name": apt_data.first_name,
        "last_name": apt_data.last_name,
        "protocol_number": apt_data.protocol_number,
        "additional_protocols": apt_data.additional_protocols,
        "has_chat": apt_data.has_chat,
        "chat_platform": apt_data.chat_platform if apt_data.has_chat else None,
        "document_urls": [],
        "date": apt_data.date,
        "time_slot": apt_data.time_slot,
        "occupies_two_slots": occupies_two_slots,
        "appointment_type": "videoconferencia",
        "status": "pendente_atribuicao",
        "notes": apt_data.notes,
        "emission_system": emission_system,
        "created_by": current_user.id,
        "created_at": now_str,
        "updated_at": now_str,
        "reserved_at": now_str,
        "reschedule_reason": apt_data.reschedule_reason,
    }
    await db.appointments.insert_one(apt_doc)
    await log_appointment_history(apt_doc["id"], "created", current_user.id, current_user.name)
    return Appointment(**apt_doc)


class AppointmentRecurringCreate(BaseModel):
    first_name: str
    last_name: str
    protocol_number: str
    additional_protocols: List[str] = []
    has_chat: bool = False
    chat_platform: Optional[str] = None
    notes: Optional[str] = None
    emission_system: Optional[str] = None
    reschedule_reason: Optional[str] = None
    dates: List[str]
    time_slot: str



@api_router.post("/appointments/recurring")
async def create_recurring_appointments(
    data: AppointmentRecurringCreate,
    current_user: User = Depends(get_current_user),
):
    block_admin(current_user)
    block_agent(current_user)
    check_role_permission(
        current_user,
        [UserRole.TELEVENDAS, UserRole.COMERCIAL, UserRole.SUPERVISOR],
        "criar agendamentos recorrentes",
    )

    created = []

    for date in data.dates:
        now_str = datetime.now(timezone.utc).isoformat()
        apt_doc = {
            "id": str(uuid.uuid4()),
            "user_id": None,
            "first_name": data.first_name,
            "last_name": data.last_name,
            "protocol_number": data.protocol_number,
            "additional_protocols": data.additional_protocols,
            "has_chat": data.has_chat,
            "chat_platform": data.chat_platform if data.has_chat else None,
            "document_urls": [],
            "date": date,
            "time_slot": data.time_slot,
            "appointment_type": "videoconferencia",
            "status": "pendente_atribuicao",
            "notes": data.notes,
            "emission_system": data.emission_system,
            "created_by": current_user.id,
            "created_at": now_str,
            "updated_at": now_str,
            "reserved_at": now_str,
            "reschedule_reason": data.reschedule_reason,
            "recurring_group_id": None,
        }
        await db.appointments.insert_one(apt_doc)
        await log_appointment_history(apt_doc["id"], "created", current_user.id, current_user.name)
        created.append(apt_doc)

    recurring_group_id = str(uuid.uuid4())
    for apt in created:
        await db.appointments.update_one(
            {"id": apt["id"]},
            {"$set": {"recurring_group_id": recurring_group_id}},
        )
        apt["recurring_group_id"] = recurring_group_id

    return {
        "message": f"{len(created)} agendamento(s) recorrente(s) criado(s) com sucesso",
        "recurring_group_id": recurring_group_id,
        "appointments": created,
    }


@api_router.post("/appointments/redistribute")
async def redistribute_appointment(
    payload: Dict[str, str],
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="Apenas supervisores podem redistribuir")

    target_appointment_id = payload.get("target_appointment_id")
    if not target_appointment_id:
        raise HTTPException(status_code=400, detail="target_appointment_id é obrigatório")

    apt = await db.appointments.find_one({"id": target_appointment_id}, {"_id": 0})
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if not apt.get("emission_system"):
        raise HTTPException(status_code=400, detail="Agendamento sem sistema de emissão para redistribuição")

    system = apt["emission_system"]

    eligible_agents = await db.users.find(
        {
            "role": UserRole.AGENTE,
            "approved": True,
            f"can_{system}": True,
        },
        {"_id": 0}
    ).to_list(100)

    if not eligible_agents:
        raise HTTPException(status_code=400, detail="Nenhum agente elegível para redistribuição")

    occupied_ids = await db.appointments.find(
        {
            "date": apt["date"],
            "time_slot": apt["time_slot"],
            "status": {"$nin": ["cancelado", "pendente_atribuicao"]},
        },
        {"_id": 0, "user_id": 1}
    ).to_list(100)

    busy_user_ids = {x.get("user_id") for x in occupied_ids if x.get("user_id")}
    free_agents = [a for a in eligible_agents if a["id"] not in busy_user_ids]

    if not free_agents:
        raise HTTPException(status_code=400, detail="Nenhum agente livre para redistribuição")

    chosen = free_agents[0]

    await db.appointments.update_one(
        {"id": target_appointment_id},
        {
            "$set": {
                "user_id": chosen["id"],
                "status": "confirmado",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )

    await log_appointment_history(
        target_appointment_id,
        "redistributed",
        current_user.id,
        current_user.name,
        "user_id",
        apt.get("user_id"),
        chosen["name"],
    )

    updated = await db.appointments.find_one({"id": target_appointment_id}, {"_id": 0})
    return {
        "message": "Agendamento redistribuído com sucesso",
        "appointment": updated,
        "assigned_user": {
            "id": chosen["id"],
            "name": chosen["name"],
        },
    }


@api_router.get("/appointments/pending", response_model=List[Appointment])
async def get_pending_appointments(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(
            status_code=403,
            detail="Apenas supervisores têm acesso aos agendamentos pendentes",
        )

    appointments = await db.appointments.find(
        {"status": "pendente_atribuicao"},
        {"_id": 0},
    ).sort("created_at", -1).to_list(1000)

    return [Appointment(**apt) for apt in appointments]


@api_router.get("/appointments/available-slots")
async def get_available_slots(
    date: str,
    emission_system: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    try:
        request_date = datetime.fromisoformat(date).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Data inválida. Use o formato YYYY-MM-DD")

    now = now_br()
    today_date = now.date()
    current_time = now.strftime("%H:%M")

    if emission_system and emission_system not in ["safeweb", "serpro"]:
        raise HTTPException(status_code=400, detail="Sistema de emissão inválido")

    if request_date < today_date:
        return {
            "date": date,
            "emission_system": emission_system,
            "total_agents_with_permission": 0,
            "available_slots": [],
        }

    if request_date.weekday() >= 5:
        return {
            "date": date,
            "emission_system": emission_system,
            "total_agents_with_permission": 0,
            "available_slots": [],
        }

    normal_time_slots = [
        "08:00", "08:20", "08:40",
        "09:00", "09:20", "09:40",
        "10:00", "10:20", "10:40",
        "11:00", "11:20", "11:40",
        "12:00", "12:20",
        "13:00", "13:20", "13:40",
        "14:00", "14:20", "14:40",
        "15:00", "15:20", "15:40",
        "16:00", "16:20", "16:40",
        "17:00", "17:20", "17:40",
    ]

    extra_hours_doc = await db.extra_hours.find_one({"date": date}, {"_id": 0})
    extra_slots = extra_hours_doc.get("slots", []) if extra_hours_doc else []

    time_slots = sorted(set(normal_time_slots + extra_slots))
    slot_index_map = {slot: idx for idx, slot in enumerate(time_slots)}

    agent_query = {"role": UserRole.AGENTE, "approved": True}
    if emission_system:
        agent_query[f"can_{emission_system}"] = True

    agents = await db.users.find(agent_query, {"_id": 0}).to_list(100)
    total_agents = len(agents)

    appointments = await db.appointments.find(
        {"date": date, "status": {"$ne": "cancelado"}},
        {"_id": 0},
    ).to_list(1000)

    available_slots = []

    for slot in time_slots:
        is_past = request_date < today_date or (request_date == today_date and slot < current_time)
        is_current = request_date == today_date and slot == current_time

        if request_date == today_date and slot < current_time:
            continue

        slot_appointments = []

        for apt in appointments:
            apt_slot = apt.get("time_slot")
            if not apt_slot or apt_slot not in slot_index_map:
                continue

            apt_occupies_two = apt.get("occupies_two_slots", False)
            apt_index = slot_index_map[apt_slot]
            current_index = slot_index_map[slot]

            affects_current_slot = apt_index == current_index
            if apt_occupies_two and apt_index + 1 == current_index:
                affects_current_slot = True

            if affects_current_slot:
                slot_appointments.append(apt)

        occupied = len([
            a for a in slot_appointments
            if a.get("status") != "pendente_atribuicao"
        ])

        reserved = len([
            a for a in slot_appointments
            if a.get("status") == "pendente_atribuicao"
        ])

        available = max(0, total_agents - occupied)

        if available > 0:
            available_slots.append({
                "time_slot": slot,
                "available_agents": available,
                "total_agents": total_agents,
                "reserved": reserved,
                "status": "available",
                "is_past": is_past,
                "is_current": is_current,
                "is_extra": slot in extra_slots,
            })

    return {
        "date": date,
        "emission_system": emission_system,
        "total_agents_with_permission": total_agents,
        "available_slots": available_slots,
    }
@api_router.get("/appointments/filtered")
async def get_filtered_appointments(
    search: Optional[str] = None,
    date: Optional[str] = None,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    protocol_number: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    query: Dict[str, Any] = {}

    if current_user.role == UserRole.AGENTE:
        query["user_id"] = current_user.id

    if date:
        query["date"] = date
    if status:
        query["status"] = status
    if user_id and current_user.role in [UserRole.ADMIN, UserRole.SUPERVISOR]:
        query["user_id"] = user_id

    if first_name:
        query["first_name"] = {"$regex": first_name, "$options": "i"}
    if last_name:
        query["last_name"] = {"$regex": last_name, "$options": "i"}
    if protocol_number:
        query["protocol_number"] = {"$regex": protocol_number, "$options": "i"}

    if search:
        query["$or"] = [
            {"first_name": {"$regex": search, "$options": "i"}},
            {"last_name": {"$regex": search, "$options": "i"}},
            {"protocol_number": {"$regex": search, "$options": "i"}},
        ]

    items = await db.appointments.find(query, {"_id": 0}) \
        .sort([("date", 1), ("time_slot", 1)]).to_list(1000)

    return items


@api_router.get("/appointments/paginated")
async def get_appointments_paginated(
    page: int = 1,
    page_size: int = 20,
    date: Optional[str] = None,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    query: Dict[str, Any] = {}
    if current_user.role == UserRole.AGENTE:
        query["user_id"] = current_user.id
    if date:
        query["date"] = date
    if status:
        query["status"] = status
    if user_id and current_user.role in [UserRole.ADMIN, UserRole.SUPERVISOR]:
        query["user_id"] = user_id

    total = await db.appointments.count_documents(query)
    skip = max(page - 1, 0) * page_size

    items = await db.appointments.find(query, {"_id": 0}) \
        .sort([("date", 1), ("time_slot", 1)]) \
        .skip(skip).limit(page_size).to_list(page_size)

    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }


@api_router.get("/appointments/check-redistribution/{apt_id}")
async def check_redistribution(apt_id: str, current_user: User = Depends(get_current_user)):
    apt = await db.appointments.find_one({"id": apt_id}, {"_id": 0})
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    system = apt.get("emission_system")
    if not system:
        return {
            "can_redistribute": False,
            "reason": "Agendamento sem sistema de emissão definido",
        }

    eligible_agents = await db.users.find(
        {
            "role": UserRole.AGENTE,
            "approved": True,
            f"can_{system}": True,
        },
        {"_id": 0}
    ).to_list(100)

    occupied_ids = await db.appointments.find(
        {
            "date": apt["date"],
            "time_slot": apt["time_slot"],
            "status": {"$nin": ["cancelado", "pendente_atribuicao"]},
        },
        {"_id": 0, "user_id": 1}
    ).to_list(100)

    busy_user_ids = {x.get("user_id") for x in occupied_ids if x.get("user_id")}
    free_agents = [a for a in eligible_agents if a["id"] not in busy_user_ids]

    return {
        "can_redistribute": len(free_agents) > 0,
        "available_agents": [
            {"id": a["id"], "name": a["name"]}
            for a in free_agents
        ],
        "required_system": system,
    }


@api_router.get("/appointments/{apt_id}/history")
async def get_appointment_history(apt_id: str, current_user: User = Depends(get_current_user)):
    apt = await db.appointments.find_one({"id": apt_id}, {"_id": 0})
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    history = await db.appointment_history.find(
        {"appointment_id": apt_id},
        {"_id": 0}
    ).sort("changed_at", -1).to_list(500)

    return history


@api_router.get("/appointments/{apt_id}/recurring-info")
async def get_appointment_recurring_info(apt_id: str, current_user: User = Depends(get_current_user)):
    apt = await db.appointments.find_one({"id": apt_id}, {"_id": 0})
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    recurring_group_id = apt.get("recurring_group_id")
    if not recurring_group_id:
        return {
            "is_recurring": False,
            "group_id": None,
            "appointments": [],
        }

    items = await db.appointments.find(
        {"recurring_group_id": recurring_group_id},
        {"_id": 0}
    ).sort([("date", 1), ("time_slot", 1)]).to_list(200)

    return {
        "is_recurring": True,
        "group_id": recurring_group_id,
        "appointments": items,
    }


@api_router.put("/appointments/{apt_id}/assign", response_model=Appointment)
async def assign_appointment(apt_id: str, assign_data: AppointmentAssign, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="Apenas supervisores podem atribuir agendamentos")

    apt = await db.appointments.find_one({"id": apt_id}, {"_id": 0})
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    agent = await db.users.find_one({"id": assign_data.user_id}, {"_id": 0})
    if not agent:
        raise HTTPException(status_code=404, detail="Agente não encontrado")

    existing = await db.appointments.find_one(
        {
            "user_id": assign_data.user_id,
            "date": apt["date"],
            "time_slot": apt["time_slot"],
            "status": {"$ne": "cancelado"},
        },
        {"_id": 0},
    )
    if existing:
        raise HTTPException(status_code=400, detail="Agente já possui agendamento neste horário")

    await db.appointments.update_one(
        {"id": apt_id},
        {"$set": {"user_id": assign_data.user_id, "status": "confirmado", "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    await log_appointment_history(apt_id, "assigned", current_user.id, current_user.name, "user_id", None, agent["name"])

    updated_apt = await db.appointments.find_one({"id": apt_id}, {"_id": 0})
    return Appointment(**updated_apt)


@api_router.post("/appointments/{apt_id}/upload")
async def upload_document(apt_id: str, files: List[UploadFile] = File(...), current_user: User = Depends(get_current_user)):
    apt = await db.appointments.find_one({"id": apt_id}, {"_id": 0})
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    uploaded_filenames: List[str] = []
    for file in files:
        file_ext = Path(file.filename).suffix
        filename = f"{apt_id}_{uuid.uuid4()}{file_ext}"
        file_path = UPLOAD_DIR / filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        uploaded_filenames.append(filename)

    new_urls = apt.get("document_urls", []) + uploaded_filenames
    await db.appointments.update_one({"id": apt_id}, {"$set": {"document_urls": new_urls, "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"message": f"{len(files)} file(s) uploaded successfully", "filenames": uploaded_filenames}


@api_router.get("/appointments/{apt_id}/download/{filename}")
async def download_document(apt_id: str, filename: str, current_user: User = Depends(get_current_user)):
    apt = await db.appointments.find_one({"id": apt_id}, {"_id": 0})
    if not apt or filename not in apt.get("document_urls", []):
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename)


@api_router.delete("/appointments/{apt_id}/document/{filename}")
async def delete_document(apt_id: str, filename: str, current_user: User = Depends(get_current_user)):
    apt = await db.appointments.find_one({"id": apt_id}, {"_id": 0})
    if not apt or filename not in apt.get("document_urls", []):
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = UPLOAD_DIR / filename
    if file_path.exists():
        file_path.unlink()

    new_urls = [url for url in apt.get("document_urls", []) if url != filename]
    await db.appointments.update_one({"id": apt_id}, {"$set": {"document_urls": new_urls, "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"message": "Document deleted successfully"}


@api_router.get("/appointments", response_model=List[Appointment])
async def get_appointments(
    date: Optional[str] = None,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    query: Dict[str, Any] = {}

    if current_user.role == UserRole.AGENTE:
        query["user_id"] = current_user.id

    if date:
        query["date"] = date

    if status:
        query["status"] = status

    if user_id and current_user.role in [UserRole.ADMIN, UserRole.SUPERVISOR]:
        query["user_id"] = user_id

    appointments = await db.appointments.find(
        query,
        {"_id": 0}
    ).sort([("date", 1), ("time_slot", 1)]).to_list(1000)

    user_ids = list({
        apt.get("user_id")
        for apt in appointments
        if apt.get("user_id")
    })

    agent_names_map = {}
    if user_ids:
        users = await db.users.find(
            {"id": {"$in": user_ids}},
            {"_id": 0, "id": 1, "name": 1}
        ).to_list(200)

        agent_names_map = {
            user["id"]: user["name"]
            for user in users
        }

    enriched_appointments = []
    for apt in appointments:
        enriched_apt = {
            **apt,
            "agent_name": agent_names_map.get(apt.get("user_id"))
        }
        enriched_appointments.append(Appointment(**enriched_apt))

    return enriched_appointments

@api_router.get("/appointments/{apt_id}", response_model=Appointment)
async def get_appointment(apt_id: str, current_user: User = Depends(get_current_user)):
    apt = await db.appointments.find_one({"id": apt_id}, {"_id": 0})
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return Appointment(**apt)


@api_router.put("/appointments/{apt_id}")
async def update_appointment(apt_id: str, apt_data: AppointmentUpdate, current_user: User = Depends(get_current_user)):
    apt = await db.appointments.find_one({"id": apt_id}, {"_id": 0})
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if current_user.role != UserRole.SUPERVISOR and current_user.id not in [apt.get("created_by"), apt.get("user_id")]:
        raise HTTPException(status_code=403, detail="Apenas supervisor, criador ou agente designado podem editar")

    update_data = {k: v for k, v in apt_data.model_dump().items() if v is not None}
    
    current_additional_protocols = apt.get("additional_protocols", [])
    new_additional_protocols = update_data.get("additional_protocols", current_additional_protocols)

    total_protocols = 1 + len(new_additional_protocols)
    update_data["occupies_two_slots"] = total_protocols >= 3


    new_date = update_data.get("date", apt.get("date"))
    new_time_slot = update_data.get("time_slot", apt.get("time_slot"))
    new_emission_system = update_data.get("emission_system", apt.get("emission_system"))
    occupies_two_slots = update_data["occupies_two_slots"]

    normal_time_slots = [
        "08:00", "08:20", "08:40",
        "09:00", "09:20", "09:40",
        "10:00", "10:20", "10:40",
        "11:00", "11:20", "11:40",
        "12:00", "12:20",
        "13:00", "13:20", "13:40",
        "14:00", "14:20", "14:40",
        "15:00", "15:20", "15:40",
        "16:00", "16:20", "16:40",
        "17:00", "17:20", "17:40",
    ]

    extra_hours_doc = await db.extra_hours.find_one({"date": new_date}, {"_id": 0})
    extra_slots = extra_hours_doc.get("slots", []) if extra_hours_doc else []

    time_slots = sorted(set(normal_time_slots + extra_slots))

    if new_time_slot not in time_slots:
        raise HTTPException(status_code=400, detail="Horário selecionado é inválido para esta data")

    if occupies_two_slots:
        current_index = time_slots.index(new_time_slot)

        if current_index + 1 >= len(time_slots):
            raise HTTPException(
                status_code=400,
                detail="Este agendamento precisa de 2 horários consecutivos, mas não existe próximo horário disponível"
            )

    next_slot = time_slots[current_index + 1]

    agent_query = {"role": UserRole.AGENTE, "approved": True}
    if new_emission_system:
        agent_query[f"can_{new_emission_system}"] = True

    agents = await db.users.find(agent_query, {"_id": 0}).to_list(100)
    total_agents = len(agents)

    appointments = await db.appointments.find(
        {
            "date": new_date,
            "status": {"$ne": "cancelado"},
            "id": {"$ne": apt_id},
        },
        {"_id": 0},
    ).to_list(1000)

    slot_index_map = {slot: idx for idx, slot in enumerate(time_slots)}

    def count_occupied(target_slot: str) -> int:
        slot_appointments = []

        for other_apt in appointments:
            other_slot = other_apt.get("time_slot")
            if not other_slot or other_slot not in slot_index_map:
                continue

            other_occupies_two = other_apt.get("occupies_two_slots", False)
            other_index = slot_index_map[other_slot]
            current_slot_index = slot_index_map[target_slot]

            affects_current_slot = other_index == current_slot_index

            if other_occupies_two and other_index + 1 == current_slot_index:
                affects_current_slot = True

            if affects_current_slot:
                slot_appointments.append(other_apt)

        return len([
            a for a in slot_appointments
            if a.get("status") != "pendente_atribuicao"
        ])

    current_slot_occupied = count_occupied(new_time_slot)
    next_slot_occupied = count_occupied(next_slot)

    if current_slot_occupied >= total_agents:
        raise HTTPException(
            status_code=400,
            detail="O horário selecionado não possui disponibilidade suficiente"
        )

    if next_slot_occupied >= total_agents:
        raise HTTPException(
            status_code=400,
            detail="Este agendamento precisa de 2 horários consecutivos, mas o próximo horário não está disponível"
        )
    


    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.appointments.update_one({"id": apt_id}, {"$set": update_data})

    for field, new_value in update_data.items():
        if field != "updated_at" and apt.get(field) != new_value:
            await log_appointment_history(
                apt_id,
                "updated" if field not in ["date", "time_slot", "status"] else ("rescheduled" if field in ["date", "time_slot"] else "status_changed"),
                current_user.id,
                current_user.name,
                field,
                str(apt.get(field)) if apt.get(field) is not None else None,
                str(new_value),
            )




@api_router.delete("/appointments/{apt_id}")
async def delete_appointment(apt_id: str, current_user: User = Depends(get_current_user)):
    apt = await db.appointments.find_one({"id": apt_id}, {"_id": 0})
    if not apt:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if current_user.role != UserRole.SUPERVISOR and current_user.id != apt.get("created_by"):
        raise HTTPException(status_code=403, detail="Apenas supervisor ou criador pode excluir")

    result = await db.appointments.delete_one({"id": apt_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return {"message": "Appointment deleted"}


@api_router.put("/users/{user_id}/approve")
async def approve_user(user_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="Only supervisors can approve users")

    result = await db.users.update_one({"id": user_id}, {"$set": {"approved": True}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User approved successfully"}


@api_router.put("/users/{user_id}/role")
async def update_user_role(user_id: str, role_data: UserUpdateRole, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="Only supervisors can change user roles")

    result = await db.users.update_one({"id": user_id}, {"$set": {"role": role_data.role}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User role updated successfully"}


@api_router.put("/users/{user_id}/permissions")
async def update_user_permissions(user_id: str, perm_data: UserUpdatePermissions, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="Apenas supervisores podem alterar permissões")

    update_data: Dict[str, Any] = {}
    if perm_data.can_safeweb is not None:
        update_data["can_safeweb"] = perm_data.can_safeweb
    if perm_data.can_serpro is not None:
        update_data["can_serpro"] = perm_data.can_serpro
    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhuma permissão para atualizar")

    result = await db.users.update_one({"id": user_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return {"message": "Permissões atualizadas com sucesso"}


@api_router.get("/users/attendants", response_model=List[User])
async def get_attendants(current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="Not authorized")
    users = await db.users.find(
        {"role": UserRole.AGENTE, "approved": True},
        {"_id": 0, "password_hash": 0},
    ).to_list(100)
    return [User(**u) for u in users]




@api_router.get("/notifications", response_model=List[Notification])
async def get_notifications(read: Optional[bool] = None, current_user: User = Depends(get_current_user)):
    query: Dict[str, Any] = {"user_id": current_user.id}
    if read is not None:
        query["read"] = read
    notifications = await db.notifications.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [Notification(**n) for n in notifications]


@api_router.put("/notifications/{notif_id}/read")
async def mark_notification_read(notif_id: str, current_user: User = Depends(get_current_user)):
    await db.notifications.update_one({"id": notif_id, "user_id": current_user.id}, {"$set": {"read": True}})
    return {"message": "Notification marked as read"}


@api_router.put("/notifications/read-all")
async def mark_all_notifications_read(current_user: User = Depends(get_current_user)):
    result = await db.notifications.update_many({"user_id": current_user.id, "read": False}, {"$set": {"read": True}})
    return {"message": f"{result.modified_count} notifications marked as read"}


@api_router.delete("/notifications/{notif_id}")
async def delete_notification(notif_id: str, current_user: User = Depends(get_current_user)):
    result = await db.notifications.delete_one({"id": notif_id, "user_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification deleted"}


@api_router.post("/presence/heartbeat")
async def send_heartbeat(current_user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one({"id": current_user.id}, {"$set": {"is_online": True, "last_seen": now}})
    return {"status": "online", "timestamp": now}


@api_router.post("/presence/offline")
async def go_offline(current_user: User = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one({"id": current_user.id}, {"$set": {"is_online": False, "last_seen": now}})
    return {"status": "offline", "timestamp": now}



BR_TZ = ZoneInfo("America/Sao_Paulo")
EXTRA_TIME_SLOTS = ["07:40", "12:40", "18:00", "18:20", "18:40"]
def now_br() -> datetime:
    return datetime.now(BR_TZ)

def today_br_iso() -> str:
    return now_br().date().isoformat()

def now_br_time_str() -> str:
    return now_br().strftime("%H:%M")

@api_router.get("/stats/dashboard")
async def get_dashboard_stats(date: Optional[str] = None, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERVISOR]:
        raise HTTPException(status_code=403, detail="Not authorized")

    target_date = date or datetime.now(timezone.utc).date().isoformat()

    total = await db.appointments.count_documents({"date": target_date})
    pendentes = await db.appointments.count_documents({"date": target_date, "status": "pendente_atribuicao"})
    confirmados = await db.appointments.count_documents({"date": target_date, "status": "confirmado"})
    emitidos = await db.appointments.count_documents({"date": target_date, "status": "emitido"})
    reagendar = await db.appointments.count_documents({"date": target_date, "status": "reagendar"})
    presencial = await db.appointments.count_documents({"date": target_date, "status": "presencial"})
    cancelados = await db.appointments.count_documents({"date": target_date, "status": "cancelado"})

    agents = await db.users.find(
        {"role": UserRole.AGENTE, "approved": True},
        {"_id": 0}
    ).to_list(100)

    agent_stats = []
    for agent in agents:
        count = await db.appointments.count_documents({
            "user_id": agent["id"],
            "date": target_date,
            "status": {"$ne": "cancelado"}
        })
        agent_stats.append({
            "id": agent["id"],
            "name": agent["name"],
            "appointments": count,
            "total_appointments": count,
            "total_sessions": count,
        })

    return {
        "date": target_date,
        "total": total,
        "by_status": {
            "pendentes": pendentes,
            "confirmados": confirmados,
            "emitidos": emitidos,
            "reagendar": reagendar,
            "presencial": presencial,
            "cancelados": cancelados,
        },
        "auto_assigned": 0,
        "agents": agent_stats,
    }


@api_router.get("/presence/agents")
async def get_agents_presence(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERVISOR]:
        raise HTTPException(status_code=403, detail="Not authorized")

    agents = await db.users.find(
        {"role": UserRole.AGENTE, "approved": True},
        {"_id": 0, "password_hash": 0}
    ).to_list(100)

    now = datetime.now(timezone.utc)
    result = []
    for agent in agents:
        last_seen = agent.get("last_seen")
        is_online = agent.get("is_online", False)

        if last_seen and is_online:
            try:
                last_seen_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                minutes_ago = (now - last_seen_dt).total_seconds() / 60
                if minutes_ago > 3:
                    is_online = False
            except Exception:
                is_online = False

        result.append({
            "id": agent["id"],
            "name": agent["name"],
            "email": agent["email"],
            "is_online": is_online,
            "last_seen": last_seen,
        })

    return result

@api_router.get("/extra-hours")
async def get_extra_hours(date: str, current_user: User = Depends(get_current_user)):
    doc = await db.extra_hours.find_one({"date": date}, {"_id": 0})
    return {
        "date": date,
        "available_slots": EXTRA_TIME_SLOTS,
        "active_slots": doc.get("slots", []) if doc else [],
    }


@api_router.put("/extra-hours")
async def update_extra_hours(
    date: str,
    slots: List[str] = Query(default=[]),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="Apenas supervisores podem gerenciar horários extras")

    valid_slots = [s for s in slots if s in EXTRA_TIME_SLOTS]

    await db.extra_hours.update_one(
        {"date": date},
        {
            "$set": {
                "date": date,
                "slots": valid_slots,
                "updated_by": current_user.id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
        upsert=True,
    )

    return {
        "date": date,
        "active_slots": valid_slots,
        "message": f"{len(valid_slots)} horário(s) extra(s) ativado(s)",
    }

@api_router.get("/slots/all")
async def get_all_slots(date: str, current_user: User = Depends(get_current_user)):
    normal_slots = [
        "08:00", "08:20", "08:40",
        "09:00", "09:20", "09:40",
        "10:00", "10:20", "10:40",
        "11:00", "11:20", "11:40",
        "12:00", "12:20",
        "13:00", "13:20", "13:40",
        "14:00", "14:20", "14:40",
        "15:00", "15:20", "15:40",
        "16:00", "16:20", "16:40",
        "17:00", "17:20", "17:40",
    ]

    try:
        request_date = datetime.fromisoformat(date).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Data inválida. Use o formato YYYY-MM-DD")

    now = now_br()
    today = now.date()
    current_time = now.strftime("%H:%M")

    if request_date < today:
        return {
            "date": date,
            "total_agents": 0,
            "slots": [],
        }

    if request_date.weekday() >= 5:
        return {
            "date": date,
            "total_agents": 0,
            "slots": [],
        }

    extra_doc = await db.extra_hours.find_one({"date": date}, {"_id": 0})
    extra_slots = extra_doc.get("slots", []) if extra_doc else []

    all_slots = sorted(set(normal_slots + extra_slots))
    slot_index_map = {slot: idx for idx, slot in enumerate(all_slots)}

    agents = await db.users.find(
        {"role": UserRole.AGENTE, "approved": True},
        {"_id": 0},
    ).to_list(100)
    total_agents = len(agents)

    agent_names_map = {
        agent["id"]: agent["name"]
        for agent in agents
    }

    appointments = await db.appointments.find(
        {"date": date},
        {"_id": 0},
    ).to_list(1000)

    result = []
    for slot in all_slots:
        if request_date == today and slot <= current_time:
            continue

        slot_appointments = []

        for a in appointments:
            if a.get("status") == "cancelado":
                continue

            apt_slot = a.get("time_slot")
            if not apt_slot or apt_slot not in slot_index_map:
                continue

            occupies_two = a.get("occupies_two_slots", False)
            apt_index = slot_index_map[apt_slot]
            current_index = slot_index_map[slot]

            affects_current_slot = apt_index == current_index

            if occupies_two and apt_index + 1 == current_index:
                affects_current_slot = True

            if affects_current_slot:
                enriched_appointment = {
                    **a,
                    "agent_name": agent_names_map.get(a.get("user_id"))
                }
                slot_appointments.append(enriched_appointment)

        occupied = len([
            a for a in slot_appointments
            if a.get("status") != "pendente_atribuicao"
        ])

        pending = len([
            a for a in slot_appointments
            if a.get("status") == "pendente_atribuicao"
        ])

        available = max(0, total_agents - occupied)

        result.append({
            "time_slot": slot,
            "total_agents": total_agents,
            "occupied": occupied,
            "pending": pending,
            "available": available,
            "appointments": slot_appointments,
            "is_extra": slot in extra_slots,
            "is_past": False,
            "is_current": False,
        })

    return {
        "date": date,
        "total_agents": total_agents,
        "slots": result,
    }

class ChangePasswordRequest(BaseModel):
    current_password: Optional[str] = None
    new_password: str
    confirm_password: str


@api_router.get("/users/stats/team")
async def get_team_stats(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERVISOR]:
        raise HTTPException(status_code=403, detail="Not authorized")

    users = await db.users.find(
        {"role": UserRole.AGENTE, "approved": True},
        {"_id": 0}
    ).to_list(100)

    stats = []
    today = datetime.now(timezone.utc).date().isoformat()

    for user in users:
        appointments = await db.appointments.find(
            {
                "user_id": user["id"],
                "date": today,
                "status": {"$ne": "cancelado"},
            },
            {"_id": 0},
        ).to_list(1000)

        total_sessions = len(appointments)

        stats.append({
            "user_id": user["id"],
            "name": user["name"],
            "avatar_url": user.get("avatar_url"),
            "total_appointments": total_sessions,
            "total_sessions": total_sessions,
            "status": (
                "overloaded" if total_sessions > 15
                else "available" if total_sessions < 8
                else "normal"
            ),
        })

    return stats


@api_router.get("/users/with-permission/{system}", response_model=List[User])
async def get_users_with_permission(system: str, current_user: User = Depends(get_current_user)):
    if system not in ["safeweb", "serpro"]:
        raise HTTPException(status_code=400, detail="Sistema deve ser safeweb ou serpro")

    field = f"can_{system}"
    users = await db.users.find(
        {
            field: True,
            "role": UserRole.AGENTE,
            "approved": True,
        },
        {"_id": 0, "password_hash": 0},
    ).to_list(100)

    return [User(**u) for u in users]


@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="Only supervisors can delete users")

    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "User deleted successfully"}


@api_router.put("/users/me/password")
async def change_my_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
):
    if data.new_password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    user = await db.users.find_one({"id": current_user.id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not data.current_password:
        raise HTTPException(status_code=400, detail="Current password is required")

    if not bcrypt.verify(data.current_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    new_hash = bcrypt.hash(data.new_password)

    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"password_hash": new_hash}}
    )

    return {"message": "Password updated successfully"}


@api_router.put("/users/{user_id}/password")
async def reset_user_password(
    user_id: str,
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="Only supervisors can reset user passwords")

    if data.new_password != data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_hash = bcrypt.hash(data.new_password)

    await db.users.update_one(
        {"id": user_id},
        {"$set": {"password_hash": new_hash}}
    )

    return {"message": "Password reset successfully"}


@api_router.get("/users/{user_id}", response_model=User)
async def get_user_by_id(user_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.SUPERVISOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Acesso não autorizado")

    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return User(**user)


    


class ChangeRequestCreate(BaseModel):
    appointment_id: str
    request_type: str  # 'edit' ou 'cancel'
    reason: Optional[str] = None

    # Campos opcionais para edição
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


class BlockedSlotCreate(BaseModel):
    user_id: str
    date: str
    time_slot: str
    reason: Optional[str] = None


@api_router.post("/change-requests")
async def create_change_request(
    data: ChangeRequestCreate,
    current_user: User = Depends(get_current_user),
):
    appointment = await db.appointments.find_one({"id": data.appointment_id}, {"_id": 0})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    if data.request_type not in ["edit", "cancel"]:
        raise HTTPException(status_code=400, detail="Tipo de solicitação inválido")

    # Permissões:
    # - Supervisor pode tudo
    # - Agente responsável pode solicitar
    # - Criador do agendamento pode solicitar
    can_request = (
        current_user.role == UserRole.SUPERVISOR
        or current_user.id == appointment.get("user_id")
        or current_user.id == appointment.get("created_by")
    )

    if not can_request:
        raise HTTPException(
            status_code=403,
            detail="Apenas supervisor, agente responsável ou criador podem solicitar alteração/cancelamento"
        )

    now_str = datetime.now(timezone.utc).isoformat()

    change_request = {
        "id": str(uuid.uuid4()),
        "appointment_id": data.appointment_id,
        "request_type": data.request_type,
        "status": "pending",
        "reason": data.reason,

        "new_first_name": data.new_first_name,
        "new_last_name": data.new_last_name,
        "new_protocol_number": data.new_protocol_number,
        "new_additional_protocols": data.new_additional_protocols,
        "new_date": data.new_date,
        "new_time_slot": data.new_time_slot,
        "new_notes": data.new_notes,

        "requested_by": current_user.id,
        "requested_by_name": current_user.name,
        "created_at": now_str,
        "review_notes": None,
        "reviewed_by": None,
        "reviewed_at": None,
    }

    await db.change_requests.insert_one(change_request)

    supervisors = await db.users.find(
        {"role": UserRole.SUPERVISOR, "approved": True},
        {"_id": 0, "id": 1}
    ).to_list(100)

    action_label = "cancelamento" if data.request_type == "cancel" else "alteração"

    for supervisor in supervisors:
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": supervisor["id"],
            "type": "change_request_pending",
            "message": f"{current_user.name} solicitou {action_label} do agendamento de {appointment.get('first_name', '')} {appointment.get('last_name', '')}".strip(),
            "read": False,
            "created_at": now_str,
        })

    return change_request


@api_router.get("/change-requests")
async def get_change_requests(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    query: Dict[str, Any] = {}

    if current_user.role == UserRole.SUPERVISOR:
        if status:
            query["status"] = status
    else:
        query["requested_by"] = current_user.id
        if status:
            query["status"] = status

    items = await db.change_requests.find(query, {"_id": 0}) \
        .sort("created_at", -1).to_list(500)

    return items


@api_router.put("/change-requests/{request_id}/review")
async def review_change_request(
    request_id: str,
    approved: bool = Query(...),
    review_notes: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="Apenas supervisores podem revisar solicitações")

    request_doc = await db.change_requests.find_one({"id": request_id}, {"_id": 0})
    if not request_doc:
        raise HTTPException(status_code=404, detail="Solicitação não encontrada")

    if request_doc.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Esta solicitação já foi processada")

    appointment = await db.appointments.find_one({"id": request_doc["appointment_id"]}, {"_id": 0})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    now_str = datetime.now(timezone.utc).isoformat()
    new_status = "approved" if approved else "rejected"

    await db.change_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": new_status,
            "reviewed_by": current_user.id,
            "reviewed_at": now_str,
            "review_notes": review_notes,
        }}
    )

    if approved:
        if request_doc.get("request_type") == "cancel":
            await db.appointments.update_one(
                {"id": request_doc["appointment_id"]},
                {"$set": {
                    "status": "cancelado",
                    "updated_at": now_str
                }}
            )

            await log_appointment_history(
                request_doc["appointment_id"],
                "change_request_approved",
                current_user.id,
                current_user.name,
                field_changed="status",
                old_value=str(appointment.get("status")) if appointment.get("status") is not None else None,
                new_value="cancelado",
            )

        elif request_doc.get("request_type") == "edit":
            updates = {"updated_at": now_str}

            if request_doc.get("new_first_name") is not None:
                updates["first_name"] = request_doc["new_first_name"]
            if request_doc.get("new_last_name") is not None:
                updates["last_name"] = request_doc["new_last_name"]
            if request_doc.get("new_protocol_number") is not None:
                updates["protocol_number"] = request_doc["new_protocol_number"]
            if request_doc.get("new_additional_protocols") is not None:
                updates["additional_protocols"] = request_doc["new_additional_protocols"]
            if request_doc.get("new_date") is not None:
                updates["date"] = request_doc["new_date"]
            if request_doc.get("new_time_slot") is not None:
                updates["time_slot"] = request_doc["new_time_slot"]
            if request_doc.get("new_notes") is not None:
                updates["notes"] = request_doc["new_notes"]

            await db.appointments.update_one(
                {"id": request_doc["appointment_id"]},
                {"$set": updates}
            )

            updated_appointment = await db.appointments.find_one(
                {"id": request_doc["appointment_id"]},
                {"_id": 0}
            )

            for field in ["first_name", "last_name", "protocol_number", "additional_protocols", "date", "time_slot", "notes"]:
                old_value = appointment.get(field)
                new_value = updated_appointment.get(field)
                if old_value != new_value:
                    action = "updated"
                    if field in ["date", "time_slot"]:
                        action = "rescheduled"

                    await log_appointment_history(
                        request_doc["appointment_id"],
                        action,
                        current_user.id,
                        current_user.name,
                        field_changed=field,
                        old_value=str(old_value) if old_value is not None else None,
                        new_value=str(new_value) if new_value is not None else None,
                    )

    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": request_doc["requested_by"],
        "message": f"Sua solicitação de {'cancelamento' if request_doc.get('request_type') == 'cancel' else 'alteração'} foi {'aprovada' if approved else 'rejeitada'}",
        "type": "change_request_reviewed",
        "read": False,
        "created_at": now_str,
    })

    updated_request = await db.change_requests.find_one({"id": request_id}, {"_id": 0})
    return updated_request


@api_router.post("/blocked-slots")
async def create_blocked_slot(
    data: BlockedSlotCreate,
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="Apenas supervisores podem bloquear horários")

    user = await db.users.find_one({"id": data.user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = await db.blocked_slots.find_one(
        {
            "user_id": data.user_id,
            "date": data.date,
            "time_slot": data.time_slot,
        },
        {"_id": 0},
    )
    if existing:
        raise HTTPException(status_code=400, detail="Horário já bloqueado para este usuário")

    blocked_slot = {
        "id": str(uuid.uuid4()),
        "user_id": data.user_id,
        "date": data.date,
        "time_slot": data.time_slot,
        "reason": data.reason,
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    await db.blocked_slots.insert_one(blocked_slot)

    return {
        "message": "Horário bloqueado com sucesso",
        "blocked_slot": blocked_slot,
    }


@api_router.get("/blocked-slots")
async def get_blocked_slots(
    user_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    query: Dict[str, Any] = {}
    if user_id:
        query["user_id"] = user_id

    items = await db.blocked_slots.find(query, {"_id": 0}) \
        .sort([("date", 1), ("time_slot", 1)]).to_list(1000)

    return items


@api_router.delete("/blocked-slots/{blocked_slot_id}")
async def delete_blocked_slot(
    blocked_slot_id: str,
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.SUPERVISOR:
        raise HTTPException(status_code=403, detail="Apenas supervisores podem remover bloqueios")

    result = await db.blocked_slots.delete_one({"id": blocked_slot_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Blocked slot not found")

    return {"message": "Bloqueio removido com sucesso"}




@api_router.get("/reports/weekly-hours")
async def get_weekly_hours(
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in [UserRole.SUPERVISOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized")

    today = datetime.now(timezone.utc).date()
    weekday = today.weekday()  # segunda=0
    week_start = today - timedelta(days=weekday)
    week_end = week_start + timedelta(days=6)

    agents = await db.users.find(
        {"role": UserRole.AGENTE, "approved": True},
        {"_id": 0}
    ).to_list(100)

    result = []

    for agent in agents:
        appointments = await db.appointments.find(
            {
                "user_id": agent["id"],
                "date": {
                    "$gte": week_start.isoformat(),
                    "$lte": week_end.isoformat(),
                },
                "status": {"$ne": "cancelado"},
            },
            {"_id": 0}
        ).to_list(1000)

        emitidos = len([a for a in appointments if a.get("status") == "emitido"])
        hours_worked = emitidos  # ajuste aqui depois se a regra real for outra
        weekly_target = 40
        balance = hours_worked - weekly_target

        is_online = agent.get("is_online", False)
        last_seen = agent.get("last_seen")
        if last_seen and is_online:
            try:
                last_seen_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                minutes_ago = (datetime.now(timezone.utc) - last_seen_dt).total_seconds() / 60
                if minutes_ago > 3:
                    is_online = False
            except Exception:
                is_online = False

        result.append({
            "id": agent["id"],
            "name": agent["name"],
            "is_online": is_online,
            "emitidos": emitidos,
            "hours_worked": hours_worked,
            "weekly_target": weekly_target,
            "balance": balance,
        })

    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "agents": result,
    }

@api_router.get("/reports/daily")
async def get_daily_report(
    date: str,
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in [UserRole.SUPERVISOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized")

    appointments = await db.appointments.find(
        {"date": date},
        {"_id": 0}
    ).to_list(1000)

    total_appointments = len(appointments)

    by_status: Dict[str, int] = {}
    for apt in appointments:
        status = apt.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1

    agents = await db.users.find(
        {"role": UserRole.AGENTE, "approved": True},
        {"_id": 0}
    ).to_list(100)

    agent_rows = []
    total_hours_worked = 0

    for agent in agents:
        agent_appointments = [
            apt for apt in appointments
            if apt.get("user_id") == agent["id"] and apt.get("status") != "cancelado"
        ]

        agent_by_status: Dict[str, int] = {}
        for apt in agent_appointments:
            status = apt.get("status", "unknown")
            agent_by_status[status] = agent_by_status.get(status, 0) + 1

        emitidos = agent_by_status.get("emitido", 0)
        hours_worked = emitidos  # ajuste aqui depois se sua regra de horas for diferente

        total_hours_worked += hours_worked

        agent_rows.append({
            "id": agent["id"],
            "name": agent["name"],
            "total": len(agent_appointments),
            "by_status": agent_by_status,
            "hours_worked": hours_worked,
        })

    return {
        "summary": {
            "total_appointments": total_appointments,
            "by_status": by_status,
            "total_hours_worked": total_hours_worked,
            "auto_assigned": 0,
        },
        "agents": agent_rows,
        "appointments": appointments,
    }


class TemplateCreate(BaseModel):
    name: str
    content: str
    category: Optional[str] = "general"
    is_active: bool = True


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None


@api_router.post("/templates")
async def create_template(
    data: TemplateCreate,
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in [UserRole.SUPERVISOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized")

    existing = await db.templates.find_one({"name": data.name}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Já existe um template com esse nome")

    template = {
        "id": str(uuid.uuid4()),
        "name": data.name,
        "content": data.content,
        "category": data.category or "general",
        "is_active": data.is_active,
        "usage_count": 0,
        "created_by": current_user.id,
        "created_by_name": current_user.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    await db.templates.insert_one(template)
    return {"message": "Template criado com sucesso", "template": template}


@api_router.get("/templates")
async def get_templates(
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(get_current_user),
):
    query: Dict[str, Any] = {}

    if category:
        query["category"] = category
    if is_active is not None:
        query["is_active"] = is_active

    items = await db.templates.find(query, {"_id": 0}) \
        .sort("name", 1).to_list(500)

    return items


@api_router.get("/templates/{template_id}")
async def get_template_by_id(
    template_id: str,
    current_user: User = Depends(get_current_user),
):
    template = await db.templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return template


@api_router.put("/templates/{template_id}")
async def update_template(
    template_id: str,
    data: TemplateUpdate,
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in [UserRole.SUPERVISOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized")

    template = await db.templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        return {"message": "Nada para atualizar", "template": template}

    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    await db.templates.update_one(
        {"id": template_id},
        {"$set": update_data},
    )

    updated = await db.templates.find_one({"id": template_id}, {"_id": 0})
    return {"message": "Template atualizado com sucesso", "template": updated}


@api_router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in [UserRole.SUPERVISOR, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.templates.delete_one({"id": template_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")

    return {"message": "Template removido com sucesso"}


@api_router.post("/templates/{template_id}/use")
async def use_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
):
    template = await db.templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    await db.templates.update_one(
        {"id": template_id},
        {
            "$inc": {"usage_count": 1},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
        },
    )

    updated = await db.templates.find_one({"id": template_id}, {"_id": 0})
    return {
        "message": "Template utilizado com sucesso",
        "template": updated,
        "content": updated.get("content"),
    }


@api_router.post("/templates/from-appointment/{apt_id}")
async def create_template_from_appointment(
    apt_id: str,
    template_name: str = Query(...),
    current_user: User = Depends(get_current_user),
):
    appointment = await db.appointments.find_one({"id": apt_id}, {"_id": 0})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    existing = await db.templates.find_one({"name": template_name}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Já existe um template com esse nome")

    content_lines = [
        f"Cliente: {appointment.get('first_name', '')} {appointment.get('last_name', '')}".strip(),
        f"Protocolo: {appointment.get('protocol_number', '')}",
        f"Data: {appointment.get('date', '')}",
        f"Horário: {appointment.get('time_slot', '')}",
        f"Status: {appointment.get('status', '')}",
        f"Sistema: {appointment.get('emission_system', '') or 'N/A'}",
        f"Observações: {appointment.get('notes', '') or ''}",
    ]
    content = "\n".join(content_lines)

    template = {
        "id": str(uuid.uuid4()),
        "name": template_name,
        "content": content,
        "category": "appointment",
        "is_active": True,
        "usage_count": 0,
        "source_appointment_id": apt_id,
        "created_by": current_user.id,
        "created_by_name": current_user.name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    await db.templates.insert_one(template)

    return {
        "message": "Template criado a partir do agendamento com sucesso",
        "template": template,
    }

@api_router.get("/my-appointments")
async def get_my_appointments(
    date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    query: Dict[str, Any] = {}

    if current_user.role == UserRole.AGENTE:
        query["user_id"] = current_user.id
    elif current_user.role in [UserRole.TELEVENDAS, UserRole.COMERCIAL]:
        query["created_by"] = current_user.id
    else:
        query["$or"] = [
            {"created_by": current_user.id},
            {"user_id": current_user.id},
        ]

    if date:
        query["date"] = date

    items = await db.appointments.find(query, {"_id": 0}) \
        .sort([("date", 1), ("time_slot", 1)]) \
        .to_list(1000)

    user_ids = list({
        item.get("user_id")
        for item in items
        if item.get("user_id")
    })

    agent_names_map = {}
    if user_ids:
        users = await db.users.find(
            {"id": {"$in": user_ids}},
            {"_id": 0, "id": 1, "name": 1}
        ).to_list(200)

        agent_names_map = {
            user["id"]: user["name"]
            for user in users
        }

    enriched_items = []
    for item in items:
        enriched_item = {
            **item,
            "agent_name": agent_names_map.get(item.get("user_id"))
        }
        enriched_items.append(enriched_item)

    return enriched_items
    
@api_router.get("/my-appointments/stats")
async def get_my_appointments_stats(
    current_user: User = Depends(get_current_user),
):
    query: Dict[str, Any] = {}

    if current_user.role == UserRole.AGENTE:
        query["user_id"] = current_user.id

    elif current_user.role in [UserRole.TELEVENDAS, UserRole.COMERCIAL]:
        query["created_by"] = current_user.id

    else:
        query["$or"] = [
            {"created_by": current_user.id},
            {"user_id": current_user.id},
        ]

    all_appointments = await db.appointments.find(query, {"_id": 0}).to_list(1000)


    today = today_br_iso()
    return {
        "total": len(all_appointments),
        "today": len([a for a in all_appointments if a.get("date") == today]),
        "pending": len([a for a in all_appointments if a.get("status") == "pendente_atribuicao"]),
        "emitidos": len([a for a in all_appointments if a.get("status") == "emitido"]),
        "pending_requests": 0
    }

app.include_router(api_router)


@app.on_event("shutdown")
async def shutdown_event():
    client.close()
    
