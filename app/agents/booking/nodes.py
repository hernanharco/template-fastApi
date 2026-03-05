import json
import logging
from datetime import datetime, timedelta
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from app.core.config import settings
from app.agents.booking.tools import search_slots_tool, find_service_by_name
from app.agents.routing.state import RoutingState

logger = logging.getLogger(__name__)

async def booking_node(state: RoutingState):
    """
    🎯 SRP: Gestión de disponibilidad con inteligencia temporal avanzada.
    Maneja búsquedas por día, tarde/mañana, apertura/cierre y límites de hora.
    """
    llm = ChatOpenAI(
        model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY, temperature=0
    )
    user_input = state["messages"][-1].content
    active_slots = state.get("active_slots", [])
    
    # ---------------------------------------------------------
    # 1. CLASIFICACIÓN DE INTENCIÓN (SELECT vs SEARCH)
    # ---------------------------------------------------------
    intent_prompt = (
        "Determina si el usuario está eligiendo una opción existente o buscando algo nuevo.\n"
        f"Contexto de slots actuales: {active_slots}\n"
        "SELECT: Si dice 'la 1', 'la primera', 'a las 10:00' (si esa hora coincide con la lista).\n"
        "SEARCH: Si pide otro día, otra hora, 'más tarde', 'mañana', 'el lunes', o un servicio.\n"
        "Responde SOLO la palabra: SELECT o SEARCH."
    )
    
    intent_res = await llm.ainvoke([("system", intent_prompt), ("user", user_input)])
    intent = intent_res.content.strip().upper()

    if "SELECT" in intent and active_slots:
        return {
            "current_step": "CONFIRMING_APPOINTMENT",
            "next_action": "CONFIRM",
            "user_selection_raw": user_input,
        }

    # ---------------------------------------------------------
    # 2. EXTRACCIÓN TEMPORAL AVANZADA (El "Cerebro" del tiempo)
    # ---------------------------------------------------------
    now = datetime.now()
    hoy_str = now.strftime('%Y-%m-%d')
    hora_actual = now.strftime('%H:%M')
    
    # Contexto para obligar a la IA a usar HOY por defecto
    ctx_temporal = (
        f"FECHA DE HOY: {now.strftime('%A, %d de %B de %Y')}\n"
        f"HORA ACTUAL: {hora_actual}\n\n"
        "REGLAS CRÍTICAS:\n"
        f"1. Si el usuario NO menciona un día específico, USA SIEMPRE '{hoy_str}'.\n"
        "2. 'Mañana' es el día siguiente a hoy.\n"
        "3. 'Otro día' es el día siguiente al que se estaba consultando."
    )

    extraction_prompt = (
        f"{ctx_temporal}\n\n"
        "Analiza el deseo del usuario y extrae los filtros en JSON.\n"
        "PREFERENCIAS:\n"
        "- 'EARLIEST': Apertura, mañana, lo más pronto.\n"
        "- 'LATEST': Cierre, tarde, última hora.\n"
        "- 'BEFORE_X': Antes de una hora (HH:MM).\n"
        "- 'AFTER_X': Después de una hora (HH:MM).\n"
        "- 'NONE': Sin preferencia.\n\n"
        "Devuelve este JSON:\n"
        "{\n"
        '  "target_date": "YYYY-MM-DD",\n'
        '  "preference": "EARLIEST | LATEST | BEFORE_X | AFTER_X | NONE",\n'
        '  "time_limit": "HH:MM o null"\n'
        "}"
    )

    try:
        res = await llm.ainvoke([("system", extraction_prompt), ("user", user_input)])
        data = json.loads(res.content.replace("```json", "").replace("```", "").strip())
        # Seguridad: Si la IA devuelve una fecha pasada, forzamos hoy
        if data.get("target_date") < hoy_str:
            data["target_date"] = hoy_str
    except:
        data = {"target_date": hoy_str, "preference": "NONE", "time_limit": None}

    # ---------------------------------------------------------
    # 3. BÚSQUEDA EN BASE DE DATOS
    # ---------------------------------------------------------
    service_id = state.get("selected_service_id")
    search_date = data.get("target_date")

    availability = search_slots_tool(
        client_phone=state["client_phone"],
        service_id=service_id,
        target_date=search_date
    )

    if not availability.get("success") or not availability.get("options"):
        # Si no hay nada hoy, intentamos mañana automáticamente para no dar error
        if search_date == hoy_str:
            manana = (now + timedelta(days=1)).strftime('%Y-%m-%d')
            availability = search_slots_tool(
                client_phone=state["client_phone"],
                service_id=service_id,
                target_date=manana
            )
            search_date = manana
        
        # Si después del re-intento sigue vacío:
        if not availability.get("options"):
            return {
                "messages": [AIMessage(content=f"✨ *No cuento con espacios disponibles para el {search_date}*.\n\n¿Te gustaría que busquemos en otra fecha?")],
                "active_slots": [],
                "next_action": "FINISH"
            }

    # ---------------------------------------------------------
    # 4. FILTRADO INTELIGENTE Y TEMPORAL
    # ---------------------------------------------------------
    slots = availability["options"]
    
    # 🚀 FILTRO CRÍTICO: Si es hoy, eliminar horas que ya pasaron
    if search_date == hoy_str:
        slots = [s for s in slots if s["time"] > hora_actual]

    pref = data.get("preference")
    limit = data.get("time_limit")

    if pref == "BEFORE_X" and limit:
        slots = [s for s in slots if s["time"] <= limit]
    elif pref == "AFTER_X" and limit:
        slots = [s for s in slots if s["time"] >= limit]
    
    # Ordenar según preferencia (Mantenemos tu lógica)
    if pref == "EARLIEST":
        slots = sorted(slots, key=lambda x: x["time"])[:3]
    elif pref == "LATEST":
        slots = sorted(slots, key=lambda x: x["time"], reverse=True)[:3]
        slots = sorted(slots, key=lambda x: x["time"]) 
    else:
        slots = slots[:3]

    # Re-chequeo por si el filtro de "hora actual" dejó la lista vacía
    if not slots:
        return {
            "messages": [AIMessage(content=f"Lo siento, para el día de hoy ya no me quedan citas disponibles después de las {hora_actual}. ¿Te gustaría buscar para mañana?")],
            "active_slots": [],
            "next_action": "FINISH"
        }

    # ---------------------------------------------------------
    # 5. RESPUESTA PREMIUM LUXURY ✨ (Exactamente igual a la tuya)
    # ---------------------------------------------------------
    msg_options = "\n".join([f"🔹 *{i+1}.* {s['time']}" for i, s in enumerate(slots)])
    
    fecha_dt = datetime.strptime(search_date, "%Y-%m-%d")
    fecha_bonita = fecha_dt.strftime("%A, %d de %B")

    texto_final = (
        f"📅 *Disponibilidad para el {fecha_bonita}*\n\n"
        "He encontrado estos espacios exclusivos para ti:\n\n"
        f"{msg_options}\n\n"
        "━━━━━━━━━━━━━━\n"
        "👉 *¿Qué horario te sienta mejor?* (Indica el número)"
    )

    return {
        "messages": [AIMessage(content=texto_final)],
        "active_slots": slots,
        "selected_service_id": service_id,
        "current_step": "AWAITING_SLOT_SELECTION",
        "next_action": "FINISH",
    }