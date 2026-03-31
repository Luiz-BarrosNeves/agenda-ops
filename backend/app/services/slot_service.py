"""
Serviço de gerenciamento de slots de horário
"""
from datetime import datetime
from zoneinfo import ZoneInfo
BR_TZ = ZoneInfo("America/Sao_Paulo")
from typing import List, Dict, Any, Optional
from ..config import DEFAULT_TIME_SLOTS, EXTRA_TIME_SLOTS

class SlotService:
    """Serviço para gerenciamento de slots de horário"""
    
    @staticmethod
    def get_default_slots() -> List[str]:
        """Retorna a lista de slots padrão"""
        return DEFAULT_TIME_SLOTS.copy()
    
    @staticmethod
    def get_extra_slots() -> List[str]:
        """Retorna a lista de slots extras"""
        return EXTRA_TIME_SLOTS.copy()
    
    @staticmethod
    def get_all_possible_slots() -> List[str]:
        """Retorna todos os slots possíveis (padrão + extras)"""
        all_slots = DEFAULT_TIME_SLOTS + EXTRA_TIME_SLOTS
        return sorted(set(all_slots))
    
    @staticmethod
    def is_slot_current(time_slot: str) -> bool:
        """Verifica se o slot é o atual baseado na hora"""
        now = datetime.now(BR_TZ)
        current_hour = now.hour
        current_minute = now.minute
        
        try:
            slot_hour, slot_minute = map(int, time_slot.split(':'))
            # Considera "atual" se estiver dentro de 20 minutos
            slot_total_minutes = slot_hour * 60 + slot_minute
            current_total_minutes = current_hour * 60 + current_minute
            
            return slot_total_minutes <= current_total_minutes < slot_total_minutes + 20
        except:
            return False
    
    @staticmethod
    def is_slot_past(time_slot: str) -> bool:
        """Verifica se o slot já passou"""
        now = datetime.now(BR_TZ)
        current_hour = now.hour
        current_minute = now.minute
        
        try:
            slot_hour, slot_minute = map(int, time_slot.split(':'))
            slot_total_minutes = slot_hour * 60 + slot_minute
            current_total_minutes = current_hour * 60 + current_minute
            
            return current_total_minutes > slot_total_minutes + 20
        except:
            return False
    
    @staticmethod
    def get_next_slot(current_slot: str) -> Optional[str]:
        """Retorna o próximo slot após o informado"""
        all_slots = sorted(DEFAULT_TIME_SLOTS + EXTRA_TIME_SLOTS)
        try:
            current_idx = all_slots.index(current_slot)
            if current_idx < len(all_slots) - 1:
                return all_slots[current_idx + 1]
        except ValueError:
            pass
        return None
    
    @staticmethod
    def calculate_slot_availability(
        time_slot: str,
        total_agents: int,
        appointments: List[Dict[str, Any]],
        is_extra: bool = False
    ) -> Dict[str, Any]:
        """Calcula a disponibilidade de um slot"""
        occupied = len([a for a in appointments if a.get('time_slot') == time_slot])
        
        return {
            'time_slot': time_slot,
            'total': total_agents,
            'occupied': occupied,
            'available': max(0, total_agents - occupied),
            'is_extra': is_extra
        }
