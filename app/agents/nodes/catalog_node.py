# app/agents/nodes/catalog_node.py

from app.agents.routing.intent import Intent
from app.agents.routing.state import RoutingState
from app.agents.tools.get_catalog_tool import get_catalog_tool
from app.agents.tools.find_service_by_text_tool import find_service_by_text_tool
from app.agents.formatters.catalog_formatter import format_catalog_for_whatsapp
from app.db.session import SessionLocal


def _get_last_user_message(state: RoutingState) -> str:
    """
    Extrae el último mensaje del usuario desde state["messages"].
    """
    messages = state.get("messages", [])

    if not messages:
        return ""

    last_message = messages[-1]
    return (last_message.get("content") or "").strip()


def catalog_node(state: RoutingState) -> RoutingState:
    """
    Nodo responsable de:
    1. Mostrar catálogo cuando aún no hay servicio elegido
    2. Resolver el texto del usuario a un servicio real
    3. Pasar a BOOKING cuando el usuario ya eligió servicio
    """

    client_name = state.get("client_name")
    shown_service_ids = state.get("shown_service_ids", [])
    user_text = _get_last_user_message(state)

    db = SessionLocal()

    try:
        # 1) Intentar resolver si el usuario ya escribió un servicio
        if user_text:
            matched_service = find_service_by_text_tool(
                db=db,
                user_text=user_text,
                shown_service_ids=shown_service_ids,
            )

            if matched_service:
                return {
                    "selected_service_id": matched_service.id,
                    "response_text": (
                        f"Perfecto, has elegido *{matched_service.name}* 😊\n\n"
                        "Ahora voy a buscar los horarios disponibles para ti."
                    ),
                    "intent": Intent.BOOKING,
                }

        # 2) Si no hubo match, mostrar catálogo
        services = get_catalog_tool(db=db)
        shown_ids = [service.id for service in services]

        return {
            "response_text": format_catalog_for_whatsapp(
                services=services,
                client_name=client_name,
            ),
            "shown_service_ids": shown_ids,
            "intent": Intent.FINISH,
        }

    finally:
        db.close()