import json
from datetime import datetime
from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.agents.appointments.tools import search_slots_tool, book_appointment_tool

async def confirmation_node(state):
    """
    🎯 SRP: Confirmar la cita elegida por el usuario.
    """
    user_input = state["messages"][-1].content
    active_slots = state.get("active_slots", [])
    
    # 1. Identificar selección (Regex para el número)
    import re
    match = re.search(r'\b([1-9])\b', user_input)
    if not match or not active_slots:
        return {"messages": [("ai", "No entendí tu elección. ¿Podrías decirme el número de la opción?")], "next_action": "FINISH"}

    idx = int(match.group(1)) - 1
    slot = active_slots[idx]

    # 2. Confirmar en DB
    reserva = await book_appointment_tool(
        client_phone=state["client_phone"],
        service_id=state["selected_service_id"],
        colab_id=slot["collaborator_id"],
        dt_str=slot["full_datetime"]
    )

    # 3. Respuesta final (usamos el mensaje que ya trae el link de Telegram)
    mensaje_final = reserva.get("message") if reserva.get("success") else "Hubo un error al reservar."
    
    return {
        "messages": [("ai", mensaje_final)],
        "active_slots": [],         # Limpieza
        "current_step": None,
        "selected_service_id": None, # Limpieza
        "next_action": "FINISH"
    }