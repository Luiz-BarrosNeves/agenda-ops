from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
from ..utils.database import get_db
from app.utils.auth import get_current_user
from passlib.hash import bcrypt
import uuid

router = APIRouter()

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class PasswordResetRequest(BaseModel):
    new_password: str
    confirm_password: str


# Removido bloco duplicado de imports/classes e router

@router.put('/me/password')
async def change_my_password(
    data: PasswordChangeRequest,
    current_user = Depends(get_current_user)
):
    import logging
    logging.getLogger(__name__).warning('[ROTA users.py change_my_password] entrou na rota')
    db = get_db()
    user = await db.users.find_one({'id': current_user.id})
    if not user:
        raise HTTPException(status_code=404, detail='Usuário não encontrado')
    if not bcrypt.verify(data.current_password, user['password_hash']):
        raise HTTPException(status_code=400, detail='Senha atual incorreta')
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail='A nova senha deve ter pelo menos 8 caracteres')
    if data.new_password != data.confirm_password:
        raise HTTPException(status_code=400, detail='A confirmação da nova senha não confere')
    new_hash = bcrypt.hash(data.new_password)
    await db.users.update_one({'id': current_user.id}, {'$set': {'password_hash': new_hash}})
    # Log/auditoria opcional
    await db.audit.insert_one({
        'id': str(uuid.uuid4()),
        'user_id': current_user.id,
        'action': 'change_password',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'details': {'ip': None, 'user_agent': None}
    })
    return {"message": "Senha atualizada"}

@router.put('/{user_id}/password')
async def reset_user_password(
    user_id: str,
    data: PasswordResetRequest,
    current_user = Depends(get_current_user)
):
    import logging
    logging.getLogger(__name__).warning('[ROTA users.py reset_user_password] entrou na rota')
    db = get_db()
    # Permitir apenas supervisor ou admin
    if current_user.role not in ('supervisor', 'admin'):
        raise HTTPException(status_code=403, detail='Apenas supervisor ou admin pode resetar senha de outro usuário')
    if len(data.new_password) < 8:
        raise HTTPException(status_code=400, detail='A nova senha deve ter pelo menos 8 caracteres')
    if data.new_password != data.confirm_password:
        raise HTTPException(status_code=400, detail='A confirmação da nova senha não confere')
    user = await db.users.find_one({'id': user_id})
    if not user:
        raise HTTPException(status_code=404, detail='Usuário não encontrado')
    new_hash = bcrypt.hash(data.new_password)
    await db.users.update_one({'id': user_id}, {'$set': {'password_hash': new_hash}})
    # Log/auditoria opcional
    await db.audit.insert_one({
        'id': str(uuid.uuid4()),
        'user_id': user_id,
        'action': 'reset_password',
        'performed_by': current_user.id,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'details': {'ip': None, 'user_agent': None}
    })
    return {"message": "Senha atualizada"}

# ...existing code...
    """Get all users (supervisor only)"""
    if current_user.role != 'supervisor':
        raise HTTPException(status_code=403, detail='Only supervisors can manage users')
    
    db = get_db()
    query = {}
    if pending_approval is not None:
        query['approved'] = not pending_approval
    
    users = await db.users.find(query, {'_id': 0, 'password_hash': 0}).to_list(100)
    return [UserResponse(**u) for u in users]


@router.put('/{user_id}/approve')
async def approve_user(user_id: str, current_user = Depends(get_current_user)):
    """Approve a pending user"""
    if current_user.role != 'supervisor':
        raise HTTPException(status_code=403, detail='Only supervisors can approve users')
    
    db = get_db()
    result = await db.users.update_one(
        {'id': user_id},
        {'$set': {'approved': True}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail='User not found')
    
    return {'message': 'User approved successfully'}


class UserUpdateRole(BaseModel):
    role: str

@router.put('/{user_id}/role')
async def update_user_role(
    user_id: str,
    role_data: UserUpdateRole,
    current_user = Depends(get_current_user)
):
    """Update user role"""
    if current_user.role != 'supervisor':
        raise HTTPException(status_code=403, detail='Only supervisors can change user roles')
    
    db = get_db()
    result = await db.users.update_one(
        {'id': user_id},
        {'$set': {'role': role_data.role}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail='User not found')
    
    return {'message': 'User role updated successfully'}


class UserUpdatePermissions(BaseModel):
    can_safeweb: Optional[bool] = None
    can_serpro: Optional[bool] = None

@router.put('/{user_id}/permissions')
async def update_user_permissions(
    user_id: str,
    perm_data: UserUpdatePermissions,
    current_user = Depends(get_current_user)
):
    """Update Safeweb/Serpro permissions"""
    if current_user.role not in ['supervisor', 'admin']:
        raise HTTPException(status_code=403, detail='Apenas supervisores podem alterar permissões')
    
    db = get_db()
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


@router.get('/with-permission/{system}')
async def get_users_with_permission(
    system: str,
    current_user = Depends(get_current_user)
):
    """Get users with specific system permission"""
    if system not in ['safeweb', 'serpro']:
        raise HTTPException(status_code=400, detail='Sistema deve ser safeweb ou serpro')
    
    db = get_db()
    field = f'can_{system}'
    users = await db.users.find({
        field: True,
        'role': 'agente',
        'approved': True
    }, {'_id': 0, 'password_hash': 0}).to_list(100)
    

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

    # ...existing code...


@router.delete('/{user_id}')
async def delete_user(user_id: str, current_user = Depends(get_current_user)):
    """Delete a user"""
    if current_user.role != 'supervisor':
        raise HTTPException(status_code=403, detail='Only supervisors can delete users')
    
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail='Cannot delete yourself')
    
    db = get_db()
    result = await db.users.delete_one({'id': user_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail='User not found')
    
    return {'message': 'User deleted successfully'}


@router.get('/attendants', response_model=List[UserResponse])
async def get_attendants(current_user = Depends(get_current_user)):
    """Get all approved agents (supervisor only)"""
    if current_user.role != 'supervisor':
        raise HTTPException(status_code=403, detail='Not authorized')
    
    db = get_db()
    users = await db.users.find({
        'role': 'agente',
        'approved': True
    }, {'_id': 0, 'password_hash': 0}).to_list(100)
    
    return [UserResponse(**u) for u in users]


@router.get('/stats/team')
async def get_team_stats(current_user = Depends(get_current_user)):
    """Get team statistics"""
    if current_user.role not in ['admin', 'supervisor']:
        raise HTTPException(status_code=403, detail='Not authorized')
    
    db = get_db()
    users = await db.users.find({
        'role': 'agente',
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
