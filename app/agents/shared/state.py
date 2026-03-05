# app/agents/core/state.py
from typing import Annotated, TypedDict, Optional
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """
    Define el estado compartido de la conversación.
    """

    # 'add_messages' asegura que los mensajes nuevos se añadan al historial
    # en lugar de sobrescribirlo (Annotated).
    messages: Annotated[list[BaseMessage], add_messages]

    # --- Datos de Cliente ---
    client_phone: Optional[str]
    client_name: Optional[str]
    client_email: Optional[str]
    client_id: Optional[int]

    # --- Datos de Servicios ---
    service_id: Optional[int]
    service_name: Optional[str]
    service_duration: Optional[int]

    # --- Datos de Agendamiento ---
    appointment_date: Optional[str]
    appointment_time: Optional[str]
    collaborator_id: Optional[int]
    appointment_id: Optional[int]

    # --- Estado de Reserva ---
    booking_options: Optional[list]  # Opciones disponibles para que el usuario elija
    booking_options_data: Optional[dict]  # Datos completos de las opciones
    selected_option: Optional[int]  # Opción seleccionada (1 o 2)

    # --- Estado de Conversación ---
    next_node: Optional[str]
    current_step: Optional[
        str
    ]  # "greeting", "catalog", "selection", "availability", "confirmation", "completed"

    # --- Metadata y Preferencias ---
    preferred_collaborator_ids: Optional[list]
    client_notes: Optional[str]
