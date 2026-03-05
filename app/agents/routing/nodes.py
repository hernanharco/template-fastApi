import json
import logging
from rich import print as rprint
from rich.panel import Panel
from sqlalchemy import text
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage

from app.db.session import SessionLocal
from app.core.config import settings
from app.agents.routing.state import RoutingState
from app.agents.routing.tools import create_new_client, update_client_name
# Importamos el motor de reglas
from app.agents.routing.rules import evaluate_all_rules

logger = logging.getLogger(__name__)

# --- NODO 1: IDENTIFICACIÓN DE CLIENTE (SRP: Acceso a Datos) ---
async def customer_lookup_node(state: RoutingState):
    """
    🎯 Identifica si el teléfono ya existe en Neon. 
    Si no, crea un registro base.
    """
    phone = state.get("client_phone")
    if not phone:
        return {"client_name": "Invitado", "is_new_user": True, "next_action": "GREETING"}

    try:
        with SessionLocal() as db:
            query = text("SELECT full_name FROM clients WHERE phone = :phone LIMIT 1")
            result = db.execute(query, {"phone": phone}).first()

        if result:
            name = result[0]
            # Si el nombre es el genérico de sistema, lo tratamos como nuevo para pedirle el nombre real
            is_new = True if name == "Nuevo Cliente" else False
            return {"client_name": name, "is_new_user": is_new}

        # Si el teléfono no está en la DB, creamos el prospecto
        create_new_client(phone=phone)
        return {"client_name": "Nuevo Cliente", "is_new_user": True, "next_action": "GREETING"}
        
    except Exception as e:
        logger.error(f"Error en customer_lookup: {e}")
        return {"client_name": "Nuevo Cliente", "is_new_user": True, "next_action": "GREETING"}


# --- NODO 2: ROUTER (SRP: Orquestación y Lógica Híbrida) ---
async def router_node(state: RoutingState):
    """
    🎯 Cerebro del flujo. Decide el siguiente nodo basándose en:
    1. Reglas deterministas (rápido/gratis).
    2. IA de rescate (semántico/flexible).
    """
    user_input = state["messages"][-1].content
    current_name = state.get("client_name", "Nuevo Cliente")
    shown_ids = state.get("shown_service_ids", [])
    active_slots = state.get("active_slots", [])
    
    # IMPORTANTE: Rescatamos el ID previo para mantener la persistencia
    previous_service_id = state.get("selected_service_id")

    rprint(Panel(f"[bold yellow]Router analizando:[/bold yellow] {user_input}"))

    # ---------------------------------------------------------
    # 1. CAPA DE REGLAS (Determinista - ¡CON AWAIT!)
    # ---------------------------------------------------------
    # Invocamos el motor de reglas. Usamos await porque suele ser async por la IA de fechas.
    action, selected_id = await evaluate_all_rules(
        user_input, 
        current_name, 
        shown_ids, 
        active_slots
    )

    # Persistencia: Si las reglas dicen BOOKING pero no traen ID nuevo, 
    # usamos el que ya teníamos guardado en el estado.
    final_id = selected_id if selected_id else previous_service_id

    if action:
        rprint(f"[green]✅ Decisión por reglas:[/green] {action} (ID: {final_id})")
        return {
            "next_action": action, 
            "selected_service_id": final_id
        }

    # ---------------------------------------------------------
    # 2. IA DE RESCATE (Semántica)
    # ---------------------------------------------------------
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY, temperature=0)
    
    patch_prompt = (
        f"Analiza la entrada del cliente: '{user_input}'.\n"
        f"Servicio actual en proceso (ID): {final_id}\n"
        f"IDs mostrados anteriormente: {shown_ids}.\n\n"
        "Clasifica la intención:\n"
        "- BOOKING: Si quiere una cita, cambiar fecha o elegir servicio.\n"
        "- CATALOG: Si quiere ver qué servicios hay.\n"
        "- GREETING: Si solo saluda o se presenta.\n"
        "- CONFIRMATION: Si elige un horario o confirma una cita.\n\n"
        "Responde SOLO JSON: "
        '{"intent": "BOOKING|CATALOG|GREETING|CONFIRMATION", "id": int|null}'
    )
    
    try:
        res = await llm.ainvoke([("system", patch_prompt)])
        data = json.loads(res.content.replace("```json", "").replace("```", "").strip())
        
        # Persistencia en IA: Si la IA no detecta ID nuevo, mantenemos el previo
        ia_id = data.get("id") if data.get("id") else final_id
        
        rprint(f"[bold blue]🤖 IA decidió:[/bold blue] {data['intent']} (ID: {ia_id})")

        # Captura de nombre para nuevos usuarios
        if data["intent"] == "GREETING" and current_name == "Nuevo Cliente":
            name_res = await llm.ainvoke(f"Extrae solo el nombre propio de: '{user_input}'. Si no hay, responde INVALID_NAME")
            nombre = name_res.content.strip()
            if "INVALID_NAME" not in nombre.upper():
                update_client_name(state["client_phone"], nombre)
                return {
                    "next_action": "GREETING", 
                    "client_name": nombre, 
                    "is_new_user": False,
                    "selected_service_id": ia_id
                }

        return {
            "next_action": data["intent"], 
            "selected_service_id": ia_id
        }
        
    except Exception as e:
        logger.error(f"Error en Router IA: {e}")
        # Ante la duda, mostramos el catálogo para no perder al cliente
        return {"next_action": "CATALOG", "selected_service_id": final_id}