"""
Reports Routes
==============
Handles daily and weekly reports with CSV export.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime, timezone, timedelta
import csv
import io

from ..utils.database import get_db
from ..utils.auth import get_current_user

router = APIRouter()


@router.get('/daily')
async def get_daily_report(
    date: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Generate daily report"""
    if current_user.role not in ['admin', 'supervisor']:
        raise HTTPException(status_code=403, detail='Not authorized')
    
    db = get_db()
    target_date = date or datetime.now(timezone.utc).date().isoformat()
    
    # Get all appointments for the day
    appointments = await db.appointments.find({
        'date': target_date
    }, {'_id': 0}).to_list(1000)
    
    # General stats
    total = len(appointments)
    by_status = {}
    for apt in appointments:
        status = apt.get('status', 'unknown')
        by_status[status] = by_status.get(status, 0) + 1
    
    # Per agent stats
    agents = await db.users.find({'role': 'agente', 'approved': True}, {'_id': 0}).to_list(100)
    agent_reports = []
    
    for agent in agents:
        agent_apts = [a for a in appointments if a.get('user_id') == agent['id']]
        agent_by_status = {}
        for apt in agent_apts:
            status = apt.get('status', 'unknown')
            agent_by_status[status] = agent_by_status.get(status, 0) + 1
        
        # Calculate hours worked (20 min per completed appointment)
        emitidos = agent_by_status.get('emitido', 0)
        hours_worked = (emitidos * 20) / 60
        
        agent_reports.append({
            'id': agent['id'],
            'name': agent['name'],
            'total': len(agent_apts),
            'by_status': agent_by_status,
            'hours_worked': round(hours_worked, 2)
        })
    
    # Calculate totals
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


@router.get('/weekly-hours')
async def get_weekly_hours(current_user = Depends(get_current_user)):
    """Calculate weekly hours balance per agent"""
    if current_user.role not in ['admin', 'supervisor']:
        raise HTTPException(status_code=403, detail='Not authorized')
    
    db = get_db()
    now = datetime.now(timezone.utc)
    # Calculate start of week (Monday)
    start_of_week = now - timedelta(days=now.weekday())
    start_date = start_of_week.date().isoformat()
    end_date = now.date().isoformat()
    
    agents = await db.users.find({'role': 'agente', 'approved': True}, {'_id': 0}).to_list(100)
    
    weekly_report = []
    for agent in agents:
        # Get completed appointments this week
        emitidos = await db.appointments.count_documents({
            'user_id': agent['id'],
            'date': {'$gte': start_date, '$lte': end_date},
            'status': 'emitido'
        })
        
        # Calculate hours (20 min per appointment)
        hours_worked = (emitidos * 20) / 60
        
        # Default weekly target: 40 hours
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


@router.get('/daily/csv')
async def export_daily_csv(
    date: Optional[str] = None,
    current_user = Depends(get_current_user)
):
    """Export daily report as CSV"""
    if current_user.role not in ['admin', 'supervisor']:
        raise HTTPException(status_code=403, detail='Not authorized')
    
    db = get_db()
    target_date = date or datetime.now(timezone.utc).date().isoformat()
    
    appointments = await db.appointments.find({
        'date': target_date
    }, {'_id': 0}).to_list(1000)
    
    # Get agent names
    agents = await db.users.find({'role': 'agente'}, {'_id': 0}).to_list(100)
    agent_names = {a['id']: a['name'] for a in agents}
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Horário', 'Cliente', 'Protocolo', 'Status', 
        'Agente', 'Sistema Emissão', 'Criado Por'
    ])
    
    # Data
    for apt in sorted(appointments, key=lambda x: x.get('time_slot', '')):
        writer.writerow([
            apt.get('time_slot', ''),
            f"{apt.get('first_name', '')} {apt.get('last_name', '')}",
            apt.get('protocol_number', ''),
            apt.get('status', ''),
            agent_names.get(apt.get('user_id'), 'Não atribuído'),
            apt.get('emission_system', 'Normal'),
            apt.get('created_by', '')
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=relatorio_{target_date}.csv"
        }
    )


@router.get('/weekly-hours/csv')
async def export_weekly_hours_csv(current_user = Depends(get_current_user)):
    """Export weekly hours as CSV"""
    if current_user.role not in ['admin', 'supervisor']:
        raise HTTPException(status_code=403, detail='Not authorized')
    
    # Get weekly data
    report = await get_weekly_hours(current_user)
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'Agente', 'Emitidos', 'Horas Trabalhadas', 
        'Meta Semanal', 'Saldo', 'Online'
    ])
    
    # Data
    for agent in report['agents']:
        writer.writerow([
            agent['name'],
            agent['emitidos'],
            agent['hours_worked'],
            agent['weekly_target'],
            agent['balance'],
            'Sim' if agent['is_online'] else 'Não'
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=saldo_semanal_{report['week_start']}_{report['week_end']}.csv"
        }
    )
