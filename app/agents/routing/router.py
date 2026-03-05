from langchain_openai import ChatOpenAI
from app.agents.routing.state import RoutingState
from app.core.config import settings

async def router_node(state: RoutingState):
    llm = ChatOpenAI(
        model="gpt-4o-mini", 
        temperature=0,
        api_key=settings.OPENAI_API_KEY
    )
    
    # 1. Recuperamos el contexto del estado
    user_input = state["messages"][-1].content
    has_services_shown = len(state.get("shown_service_ids", [])) > 0
    has_slots_shown = len(state.get("active_slots", [])) > 0

    # 2. Mejoramos el Prompt para que la IA sepa en qué punto estamos
    prompt = f"""Eres el clasificador de una peluquería. 
    Tu tarea es decidir el siguiente paso basado en el mensaje y el CONTEXTO actual.

    CONTEXTO ACTUAL:
    - ¿Se mostraron servicios recientemente?: {has_services_shown}
    - ¿Se mostraron horarios recientemente?: {has_slots_shown}

    REGLAS DE CLASIFICACIÓN:
    - GREETING: El usuario saluda, se presenta (ej: "Soy Hernán"), da las gracias o se despide.
    - BOOKING: El usuario quiere ver servicios, precios, O está respondiendo con un número para elegir un servicio (ej: "7").
    - CONFIRMATION: El usuario está respondiendo con un número para elegir una HORA de cita (ej: "1" o "2").
    - CATALOG: El usuario pide explícitamente ver el catálogo o lista de precios.

    Mensaje del usuario: "{user_input}"
    
    Responde ÚNICAMENTE con la etiqueta:"""
    
    response = await llm.ainvoke(prompt)
    decision = response.content.strip().upper()

    # Mapeamos APPOINTMENT a BOOKING si usas ese nombre en el grafo
    if decision == "APPOINTMENT": decision = "BOOKING"

    return {"next_action": decision}