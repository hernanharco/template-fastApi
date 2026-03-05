from typing import Annotated, List, Optional, Union, Dict
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

# --- REDUCERS (Los pegamentos de la memoria) ---

def merge_ids(old_ids: Optional[List[int]], new_ids: Optional[List[int]]) -> List[int]:
    return new_ids if new_ids is not None and len(new_ids) > 0 else (old_ids or [])

def merge_slots(old_slots: Optional[List[dict]], new_slots: Optional[List[dict]]) -> List[dict]:
    return new_slots if new_slots is not None and len(new_slots) > 0 else (old_slots or [])

class RoutingState(TypedDict):
    # Historial de chat
    messages: Annotated[list, add_messages]
    
    # Memoria de Catálogo
    shown_service_ids: Annotated[List[int], merge_ids]
    selected_service_id: Optional[int]
    
    # 🌟 NUEVA INTELIGENCIA TEMPORAL (Extraída por rules.py)
    selected_date: Optional[str]        # Formato: 2026-03-05
    time_filter: Optional[str]          # Formato: 15:00
    selection_preference: Optional[str]  # FIRST | LAST | ANY
    
    # Memoria de Booking (Horarios)
    active_slots: Annotated[List[Dict], merge_slots] 
    booking_for_name: Optional[str]
    other_day_attempts: int
    
    # Control de flujo y usuario
    next_action: str
    client_phone: str
    client_name: Optional[str]
    is_new_user: bool