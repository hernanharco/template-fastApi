# app/agents/agent_state.py
from typing import TypedDict, Annotated, List, Optional
import operator

class AgentState(TypedDict):
    messages: Annotated[List[dict], operator.add]
    
    # Datos compartidos
    client_name: Optional[str]
    phone: Optional[str]
    
    # Datos de Reserva (Usa estos nombres en TODOS lados)
    appointment_date: Optional[str] 
    appointment_time: Optional[str]
    service_type: Optional[str]
    service_id: Optional[int]
    
    # Filtros y Resultados
    min_time: Optional[str] 
    available_slots: Optional[str]
    
    # Estados de control
    current_node: str
    confirmation_status: Optional[str] # confirmed, conflict, no_collaborator
    booking_confirmed: bool