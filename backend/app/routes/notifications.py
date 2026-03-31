"""
Notifications Routes
====================
Handles notification CRUD operations.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict
from typing import List, Optional

from ..utils.database import get_db
from ..utils.auth import get_current_user

router = APIRouter()


class Notification(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    user_id: str
    message: str
    type: str
    read: bool
    created_at: str


@router.get('', response_model=List[Notification])
async def get_notifications(
    read: Optional[bool] = None,
    current_user = Depends(get_current_user)
):
    """Get all notifications for current user"""
    db = get_db()
    query = {'user_id': current_user.id}
    if read is not None:
        query['read'] = read
    
    notifications = await db.notifications.find(query, {'_id': 0}).sort('created_at', -1).to_list(100)
    return [Notification(**n) for n in notifications]


@router.put('/{notif_id}/read')
async def mark_notification_read(notif_id: str, current_user = Depends(get_current_user)):
    """Mark a notification as read"""
    db = get_db()
    await db.notifications.update_one(
        {'id': notif_id, 'user_id': current_user.id},
        {'$set': {'read': True}}
    )
    return {'message': 'Notification marked as read'}


@router.put('/read-all')
async def mark_all_notifications_read(current_user = Depends(get_current_user)):
    """Mark all notifications as read"""
    db = get_db()
    result = await db.notifications.update_many(
        {'user_id': current_user.id, 'read': False},
        {'$set': {'read': True}}
    )
    return {'message': f'{result.modified_count} notifications marked as read'}


@router.delete('/{notif_id}')
async def delete_notification(notif_id: str, current_user = Depends(get_current_user)):
    """Delete a notification"""
    db = get_db()
    result = await db.notifications.delete_one({
        'id': notif_id,
        'user_id': current_user.id
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Notification not found')
    return {'message': 'Notification deleted'}


@router.delete('')
async def delete_all_read_notifications(current_user = Depends(get_current_user)):
    """Delete all read notifications"""
    db = get_db()
    result = await db.notifications.delete_many({
        'user_id': current_user.id,
        'read': True
    })
    return {'message': f'{result.deleted_count} notifications deleted'}
