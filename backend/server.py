import os
import uuid
import shutil
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, ConfigDict
from passlib.hash import bcrypt

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")

UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me")
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

print("CORS_ORIGINS:", CORS_ORIGINS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    first_name: str
    last_name: str
    protocol_number: str
    additional_protocols: List[str] = []
    has_chat: bool = False
    chat_platform: Optional[str] = None
    document_urls: List[str] = []
    date: str
    time_slot: str
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


@api_router.post("/appointments", response_model=Appointment)
async def create_appointment(apt_data: AppointmentCreate, current_user: User = Depends(get_current_user)):
    block_admin(current_user)
    block_agent(current_user)
    check_role_permission(
        current_user,
        [UserRole.TELEVENDAS, UserRole.COMERCIAL, UserRole.SUPERVISOR],
        "criar agendamentos",
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

    appointments = await db.appointments.find(query, {"_id": 0}).sort([("date", 1), ("time_slot", 1)]).to_list(1000)
    return [Appointment(**apt) for apt in appointments]


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
    if not update_data:
        return Appointment(**apt)

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

    updated_apt = await db.appointments.find_one({"id": apt_id}, {"_id": 0})
    return Appointment(**updated_apt)


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


app.include_router(api_router)


@app.on_event("shutdown")
async def shutdown_event():
    client.close()
