"""
Presence Routes
===============
Handles user presence (online/offline status) via heartbeat.
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone

from ..utils.database import get_db
from ..utils.auth import get_current_user

router = APIRouter()

PRESENCE_TIMEOUT_MINUTES = 3  # Timeout to consider user offline


@router.post('/heartbeat')
async def send_heartbeat(current_user = Depends(get_current_user)):
    """Send heartbeat to maintain online status"""
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one(
        {'id': current_user.id},
        {'$set': {'is_online': True, 'last_seen': now}}
    )
    return {'status': 'online', 'timestamp': now}


@router.post('/offline')
async def go_offline(current_user = Depends(get_current_user)):
    """Mark user as offline (on logout)"""
    db = get_db()
    await db.users.update_one(
        {'id': current_user.id},
        {'$set': {'is_online': False, 'last_seen': datetime.now(timezone.utc).isoformat()}}
    )
    return {'status': 'offline'}


@router.get('/agents')
async def get_agents_presence(current_user = Depends(get_current_user)):
    """Get presence status of all agents (supervisor only)"""
    if current_user.role not in ['admin', 'supervisor']:
        raise HTTPException(status_code=403, detail='Not authorized')
    
    db = get_db()
    agents = await db.users.find({
        'role': 'agente',
        'approved': True
    }, {'_id': 0, 'password_hash': 0}).to_list(100)
    
    now = datetime.now(timezone.utc)
    result = []
    
    for agent in agents:
        last_seen = agent.get('last_seen')
        is_online = agent.get('is_online', False)
        
        # Check if really online (recent heartbeat)
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
