import re
import json
import logging
from rich import print as rprint
from rich.panel import Panel
from sqlalchemy import text
from langchain_openai import ChatOpenAI

from app.db.session import SessionLocal
from app.core.config import settings
from app.agents.routing.state import RoutingState
from app.agents.routing.tools import create_new_client, update_client_name

logger = logging.getLogger(__name__)


async def customer_lookup_node(state: RoutingState):
    """
    🎯 SRP: Identificar si el cliente existe en NEON.
    """
    phone = state.get("client_phone")
    rprint(f"[bold blue]🔍 BUSCANDO CLIENTE:[/bold blue] {phone}")

    if not phone:
        return {
            "client_name": "Invitado",
            "is_new_user": True,
            "next_action": "GREETING",
        }

    with SessionLocal() as db:
        query = text("SELECT full_name FROM clients WHERE phone = :phone LIMIT 1")
        result = db.execute(query, {"phone": phone}).first()

    if result:
        name = result[0]
        rprint(f"[green]✅ Cliente encontrado:[/green] {name}")
        return {
            "client_name": name,
            "is_new_user": False if name != "Nuevo Cliente" else True,
        }

    rprint("[yellow]👤 Nuevo cliente detectado. Creando registro...[/yellow]")
    create_new_client(phone=phone)
    return {
        "client_name": "Nuevo Cliente",
        "is_new_user": True,
        "next_action": "GREETING",
    }


async def router_node(state: RoutingState):
    """
    🎯 SRP: Decidir el SIGUIENTE NODO.
    """
    user_input = state["messages"][-1].content
    user_input_lower = user_input.lower().strip()
    current_name = state.get("client_name", "Nuevo Cliente")
    shown_ids = state.get("shown_service_ids", [])
    active_slots = state.get("active_slots", [])

    rprint(
        Panel(
            f"[bold yellow]Router analizando:[/bold yellow] {user_input}", expand=False
        )
    )

    # 1. TRADUCCIÓN DE NÚMEROS
    match_number = re.search(r"\b([1-9]|10)\b", user_input_lower)
    if match_number and len(user_input_lower) < 12:
        index = int(match_number.group(1)) - 1
        if active_slots and 0 <= index < len(active_slots):
            return {"next_action": "CONFIRMATION"}
        if shown_ids and 0 <= index < len(shown_ids):
            return {"next_action": "BOOKING", "selected_service_id": shown_ids[index]}

    # 2. KEYWORDS
    keywords_catalog = ["servicio", "precio", "catálogo", "menú", "ofrecen", "hacen"]
    if any(kw in user_input_lower for kw in keywords_catalog):
        return {"next_action": "CATALOG"}

    # 🚀 DETECCIÓN DE SALUDOS (para clientes existentes)
    saludo_keywords = [
        "hola",
        "holaa",
        "buenos",
        "buenas",
        "qué tal",
        "que tal",
        "hi",
        "hello",
        "hey",
    ]
    if any(kw in user_input_lower for kw in saludo_keywords):
        # Si el cliente ya existe, va directo a catálogo
        if current_name != "Nuevo Cliente":
            rprint(f"[green]✅ Saludo de cliente existente → catalog[/green]")
            return {"next_action": "CATALOG"}
        # Si es nuevo, va a greeting para pedir nombre
        return {"next_action": "GREETING"}

    booking_keywords = [
        "cita",
        "reserva",
        "agendar",
        "turno",
        "cejas",
        "barba",
        "corte",
        "uñas",
    ]
    if any(kw in user_input_lower for kw in booking_keywords):
        return {"next_action": "BOOKING"}

    # 🚩 PARCHE IA (Rescate de errores como 'ceas')
    llm = ChatOpenAI(
        model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY, temperature=0
    )

    if shown_ids:
        patch_prompt = (
            f"Analiza: '{user_input}'. IDs: {shown_ids}. "
            "Si el usuario pide un servicio (ej: 'ceas'), responde el ID. "
            "Si no, clasifica como GREETING o CATALOG. "
            'Responde SOLO JSON: {"intent": "BOOKING|CATALOG|GREETING", "id": int|null}'
        )
        try:
            res = await llm.ainvoke([("system", patch_prompt)])
            data = json.loads(
                res.content.replace("```json", "").replace("```", "").strip()
            )
            if data.get("id"):
                rprint(f"[bold green]✨ IA rescató ID:[/bold green] {data['id']}")
                return {"next_action": "BOOKING", "selected_service_id": data["id"]}
        except Exception as e:
            rprint(f"[red]Error parche:[/red] {e}")

    # 3. IDENTIFICACIÓN DE NOMBRE (Solo si es nuevo cliente)
    if current_name == "Nuevo Cliente":
        system_prompt = "Responde SOLO el nombre del usuario o 'INVALID_NAME'."
        response = await llm.ainvoke([("system", system_prompt), ("user", user_input)])
        nombre_detectado = response.content.strip()

        if "INVALID_NAME" not in nombre_detectado:
            update_client_name(state["client_phone"], nombre_detectado)
            return {
                "next_action": "GREETING",
                "client_name": nombre_detectado,
                "is_new_user": False,
            }

        return {"next_action": "GREETING", "name_rejected": True, "is_new_user": True}

    # 4. CLIENTE EXISTENTE: Por defecto va a catálogo
    return {"next_action": "CATALOG"}
