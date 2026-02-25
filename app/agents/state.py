# app/agents/state.py
from typing import TypedDict, Optional, Literal, Annotated, Any
from langchain_core.messages import AnyMessage  # <--- Importación clave faltante
from langgraph.graph.message import add_messages # <--- Forma estándar de LangGraph para sumar mensajes

class AgentState(TypedDict):
    """
    Estado global del agente. 
    SRP: Mantener la verdad única de la conversación y los datos del cliente.
    """
    # LangGraph usará 'add_messages' para anexar nuevos mensajes al historial
    messages: Annotated[list[AnyMessage], add_messages]
    
    # Datos del Cliente
    client_name: Optional[str]
    client_phone: Optional[str]
    
    # Contexto de Negocio
    business_slug: str
    
    # Datos de Reserva (Agregados para el parche de Booking)
    service_id: Optional[int]
    appointment_time: Optional[str]
    
    # Metadatos de Navegación
    current_node: Optional[Literal["identity", "service_expert", "main_assistant", "booking_expert"]]
    last_updated: Optional[str]