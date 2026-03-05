import json
import logging
from datetime import datetime, timedelta
from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.agents.booking.tools import search_slots_tool, find_service_by_name
from app.agents.routing.state import RoutingState

logger = logging.getLogger(__name__)


async def booking_node(state: RoutingState):
    """
    🎯 SRP: Gestión de disponibilidad y resolución de ambigüedad en citas.
    Responsabilidad: Traducir lenguaje natural a filtros de fecha/hora y
    gestionar la selección de huecos libres.
    """
    llm = ChatOpenAI(
        model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY, temperature=0
    )
    user_input = state["messages"][-1].content
    active_slots = state.get("active_slots", [])

    # ---------------------------------------------------------
    # 1. CLASIFICACIÓN DE INTENCIÓN (Evita el bucle de bienvenida)
    # ---------------------------------------------------------
    intent_prompt = (
        "Analiza el último mensaje del usuario considerando el contexto.\n"
        f"Contexto: El usuario está viendo una lista de horarios: {active_slots}\n"
        "Determina la intención:\n"
        "- 'SELECT': Si el usuario eligió un número (1, 2) o una hora específica de la lista (ej: 'a las 11', 'la de las 12').\n"
        "- 'SEARCH': Si pide otro día, otra hora, o un servicio diferente (ej: 'otro día', 'el miércoles', 'mejor corte').\n"
        "Responde SOLO con la palabra: SELECT o SEARCH."
    )

    try:
        intent_res = await llm.ainvoke(
            [("system", intent_prompt), ("user", user_input)]
        )
        intent = intent_res.content.strip().upper()
    except Exception as e:
        logger.error(f"Error en LLM booking_node: {e}")
        # Fallback: asumir que es búsqueda si hay error
        intent = "SEARCH"

    # Si es una selección, delegamos la responsabilidad de agendar
    if "SELECT" in intent and active_slots:
        return {
            "current_step": "CONFIRMING_APPOINTMENT",
            "next_action": "CONFIRM",  # Esto le dice a graph.py que vaya al nodo de reserva
            "user_selection_raw": user_input,
        }

    # ---------------------------------------------------------
    # 2. IDENTIFICACIÓN DEL SERVICIO
    # ---------------------------------------------------------
    service_id = state.get("selected_service_id")
    if not service_id:
        match = find_service_by_name(user_input)
        if match:
            service_id = match["id"]
        else:
            # Si no hay servicio, lanzamos el catálogo (SRP: el nodo booking no vende)
            return {
                "next_action": "CATALOG",
                "messages": [
                    (
                        "ai",
                        "Para ayudarte a agendar, por favor dime qué servicio te gustaría realizarte.",
                    )
                ],
            }

    # ---------------------------------------------------------
    # 3. EXTRACCIÓN DE PARÁMETROS TEMPORALES (IA Generativa)
    # ---------------------------------------------------------
    now = datetime.now()
    ctx_temporal = f"Hoy es {now.strftime('%A %d de %B, %Y')}. Hora actual: {now.strftime('%H:%M')}."

    extraction_prompt = (
        f"{ctx_temporal}\n"
        "Extrae los deseos del usuario para la cita. "
        "Si menciona un día de la semana, calcula la fecha YYYY-MM-DD. "
        "Si dice 'otro día' sin especificar, usa mañana.\n"
        "Devuelve JSON ESTRICTO:\n"
        "{\n"
        '  "target_date": "YYYY-MM-DD o null",\n'
        '  "preference": "EARLIEST, LATEST, AFTER_X, o NONE",\n'
        '  "time_limit": "HH:MM o null",\n'
        '  "for_whom": "nombre"\n'
        "}"
    )

    res = await llm.ainvoke([("system", extraction_prompt), ("user", user_input)])
    try:
        data = json.loads(res.content.replace("```json", "").replace("```", "").strip())
    except:
        data = {"target_date": None, "preference": "NONE", "time_limit": None}

    # ---------------------------------------------------------
    # 4. CONSULTA DE DISPONIBILIDAD
    # ---------------------------------------------------------
    # Si no hay fecha en el input, probamos con hoy o mañana según la hora
    search_date = data.get("target_date") or now.strftime("%Y-%m-%d")

    availability = search_slots_tool(
        client_phone=state["client_phone"],
        service_id=service_id,
        target_date=search_date,
    )

    if not availability.get("success") or not availability.get("options"):
        return {
            "messages": [
                (
                    "ai",
                    f"Lo siento, no encontré citas disponibles para el *{search_date}*. ¿Te gustaría intentar con otra fecha?",
                )
            ],
            "active_slots": [],  # Limpiamos slots viejos para no confundir
        }

    # ---------------------------------------------------------
    # 5. FILTRADO POR PREFERENCIA (Ej: "Después de las 3")
    # ---------------------------------------------------------
    slots = availability["options"]
    if data.get("time_limit") and data.get("preference") == "AFTER_X":
        slots = [s for s in slots if s["time"] >= data["time_limit"]]

    # Limitamos a los 3 mejores para no saturar WhatsApp
    slots = slots[:3]

    # ---------------------------------------------------------
    # 6. RESPUESTA ELEGANTE (IA Luxury Style)
    # ---------------------------------------------------------
    msg_options = "\n".join([f"*{i+1}.* 🕒 {s['time']}" for i, s in enumerate(slots)])

    final_prompt = (
        f"Eres {settings.NAME_IA}, la asistente de {settings.BUSINESS_NAME}.\n"
        f"Muestra estas opciones para el día *{search_date}*:\n{msg_options}\n"
        "Instrucciones: Sé breve. Solo pide que elijan un número para confirmar."
    )

    response = await llm.ainvoke([("system", final_prompt), ("user", user_input)])

    return {
        "messages": [response],
        "active_slots": slots,
        "selected_service_id": service_id,
        "current_step": "AWAITING_SLOT_SELECTION",
        "next_action": "FINISH",
    }
