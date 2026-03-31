"""
Configurações globais da aplicação
"""
import os
from pathlib import Path

# Diretórios
ROOT_DIR = Path(__file__).parent.parent
UPLOAD_DIR = ROOT_DIR / 'uploads'
UPLOAD_DIR.mkdir(exist_ok=True)

# JWT
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'

# Timings
AUTO_ASSIGN_MINUTES = 5  # Tempo para atribuição automática
PRESENCE_TIMEOUT_MINUTES = 3  # Tempo sem heartbeat para considerar offline

# Horários de atendimento
DEFAULT_TIME_SLOTS = [
    "08:00", "08:20", "08:40", "09:00", "09:20", "09:40", 
    "10:00", "10:20", "10:40", "11:00", "11:20", "11:40",
    "12:00", "12:20",
    "13:00", "13:20", "13:40", "14:00", "14:20", "14:40",
    "15:00", "15:20", "15:40", "16:00", "16:20", "16:40",
    "17:00", "17:20", "17:40"
]

EXTRA_TIME_SLOTS = ["07:40", "18:00"]

# Status de agendamentos
APPOINTMENT_STATUSES = [
    'pendente_atribuicao',
    'confirmado',
    'emitido',
    'reagendar',
    'presencial',
    'cancelado'
]

# Roles de usuário
class UserRole:
    ADMIN = 'admin'
    SUPERVISOR = 'supervisor'
    AGENTE = 'agente'
    TELEVENDAS = 'televendas'
    COMERCIAL = 'comercial'
    
    @classmethod
    def all_roles(cls):
        return [cls.ADMIN, cls.SUPERVISOR, cls.AGENTE, cls.TELEVENDAS, cls.COMERCIAL]
    
    @classmethod
    def can_manage_users(cls, role):
        return role in [cls.ADMIN, cls.SUPERVISOR]
    
    @classmethod
    def can_assign_appointments(cls, role):
        return role in [cls.ADMIN, cls.SUPERVISOR]
    
    @classmethod
    def can_see_pending(cls, role):
        return role in [cls.ADMIN, cls.SUPERVISOR]
    
    @classmethod
    def can_see_reports(cls, role):
        return role in [cls.ADMIN, cls.SUPERVISOR]
