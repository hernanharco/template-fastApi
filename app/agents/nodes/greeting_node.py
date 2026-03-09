from app.agents.routing.intent import Intent
from app.agents.routing.state import RoutingState
from app.agents.tools.update_client_name_tool import update_client_name_tool
from app.agents.tools.get_catalog_tool import get_catalog_tool
from app.agents.validators.name_validator import (
    looks_like_real_name,
    normalize_person_name,
)
from app.agents.formatters.catalog_formatter import format_catalog_for_whatsapp
from app.db.session import SessionLocal


GREETING_WORDS = {"hola", "buenas", "hello", "hey", "holi"}


def greeting_node(state: RoutingState) -> RoutingState:
    client_name = state.get("client_name")
    wait_for_name = state.get("wait_for_name", False)
    messages = state.get("messages", [])

    last_user_message = ""
    if messages:
        last_message = messages[-1]
        if isinstance(last_message, dict):
            last_user_message = (last_message.get("content") or "").strip()

    normalized_input = last_user_message.lower()

    # Cliente sin nombre real
    if not client_name or client_name == "Nuevo Cliente":
        if not last_user_message or normalized_input in GREETING_WORDS:
            return {
                "response_text": "¡Hola! 😊 Antes de continuar, ¿me compartes tu nombre?",
                "wait_for_name": True,
                "intent": Intent.FINISH,
            }

        if wait_for_name:
            if not looks_like_real_name(last_user_message):
                return {
                    "response_text": "No estoy segura de haber entendido tu nombre 😊 ¿Me lo escribes solo como te gustaría que te llame?",
                    "wait_for_name": True,
                    "intent": Intent.FINISH,
                }

            normalized_name = normalize_person_name(last_user_message)

            db = SessionLocal()
            try:
                updated_client = update_client_name_tool(
                    phone=state["client_phone"],
                    new_name=normalized_name,
                    db=db,
                )
                services = get_catalog_tool(db=db)
            finally:
                db.close()

            catalog_text = format_catalog_for_whatsapp(
                services=services,
                client_name=normalized_name,
            )

            return {
                "client_id": updated_client.client_id,
                "client_name": updated_client.client_name,
                "preferred_collaborators": updated_client.preferred_collaborators,
                "is_new_user": updated_client.is_new_user,
                "wait_for_name": False,
                "response_text": f"Encantado, {normalized_name} 😊\n\n{catalog_text}",
                "intent": Intent.FINISH,
            }

        return {
            "response_text": "¡Hola! 😊 Antes de continuar, ¿me compartes tu nombre?",
            "wait_for_name": True,
            "intent": Intent.FINISH,
        }

    # Cliente conocido: saluda + catálogo real
    db = SessionLocal()
    try:
        services = get_catalog_tool(db=db)
    finally:
        db.close()

    catalog_text = format_catalog_for_whatsapp(
        services=services,
        client_name=client_name,
    )

    return {
        "wait_for_name": False,
        "response_text": f"¡Hola, {client_name}! 😊\n\n{catalog_text}",
        "intent": Intent.FINISH,
    }