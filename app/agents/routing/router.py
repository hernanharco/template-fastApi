import json
from rich import print as rprint
from rich.panel import Panel
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.agents.routing.state import RoutingState
from app.agents.routing.tools import update_client_name
# Importamos solo el evaluador principal
from app.agents.routing.rules import evaluate_all_rules

async def router_node(state: RoutingState):
    """🎯 SRP: Orquestador de tráfico. Decide el siguiente nodo."""
    user_input = state["messages"][-1].content
    current_name = state.get("client_name", "Nuevo Cliente")
    shown_ids = state.get("shown_service_ids", [])
    active_slots = state.get("active_slots", [])

    rprint(Panel(f"[bold yellow]Router analizando:[/bold yellow] {user_input}"))

    # 1. Ejecutar el motor de reglas (Cero IA, máxima velocidad)
    next_action, selected_id = evaluate_all_rules(user_input, current_name, shown_ids, active_slots)
    
    if next_action:
        return {"next_action": next_action, "selected_service_id": selected_id}

    # 2. Red de Seguridad: IA de Rescate (Solo si las reglas fallan)
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY, temperature=0)
    
    patch_prompt = (
        f"Analiza: '{user_input}'. IDs: {shown_ids}.\n"
        "Clasifica la intención para una peluquería.\n"
        'Responde SOLO JSON: {"intent": "BOOKING|CATALOG|GREETING|CONFIRMATION", "id": int|null}'
    )
    
    try:
        res = await llm.ainvoke([("system", patch_prompt)])
        data = json.loads(res.content.replace("```json", "").replace("```", "").strip())
        
        # Lógica especial para captura de nombre de nuevos clientes
        if data["intent"] == "GREETING" and current_name == "Nuevo Cliente":
            name_res = await llm.ainvoke(f"Extrae solo el nombre propio de: '{user_input}'. Si no hay, responde INVALID_NAME")
            nombre = name_res.content.strip()
            if "INVALID_NAME" not in nombre:
                update_client_name(state["client_phone"], nombre)
                return {"next_action": "GREETING", "client_name": nombre, "is_new_user": False}

        return {"next_action": data["intent"], "selected_service_id": data.get("id")}
    except Exception as e:
        rprint(f"[red]Error en IA de rescate: {e}[/red]")
        return {"next_action": "CATALOG"}