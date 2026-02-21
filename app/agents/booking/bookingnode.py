from app.agents.booking.fuzzy_logic import service_fuzzy_match
from app.agents.booking.nodes.availability_node import availability_node
from langchain_core.messages import AIMessage
import re

def booking_expert_node(state, db):
    """
    SRP: Nodo experto en Reservas. 
    Integra tu lógica de captura de fecha/hora y validación fuzzy.
    """
    last_msg = state["messages"][-1].content
    
    # 1. Captura de datos (tu lógica de Re y Fechas)
    time_match = re.search(r"(\d{1,2})[:.](\d{2})", last_msg)
    new_data = {}
    if time_match:
        hour, minute = time_match.groups()
        new_data["appointment_time"] = f"{hour.zfill(2)}:{minute}"

    # 2. Validación Fuzzy si no hay servicio
    if not state.get("service_id"):
        match = service_fuzzy_match(db, last_msg)
        if match:
            new_data["service_type"], new_data["service_id"] = match

    # 3. Decisión: ¿Consultamos disponibilidad o confirmamos?
    # Fusionamos los datos nuevos con el estado actual para decidir
    temp_state = {**state, **new_data}
    
    if temp_state.get("appointment_time") and temp_state.get("service_id"):
        # Aquí llamarías al nodo de confirmación final
        res_text = "¡Perfecto! Ya tengo los datos. ¿Confirmas tu cita?"
    else:
        # Usamos tu availability_node que ya es excelente
        res_text = availability_node(db, temp_state)

    return {
        **new_data,
        "messages": [AIMessage(content=res_text)],
        "current_node": "booking_expert"
    }