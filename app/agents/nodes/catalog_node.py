from app.agents.routing.intent import Intent
from app.agents.routing.state import RoutingState
from app.agents.tools.get_catalog_tool import get_catalog_tool
from app.agents.tools.find_service_by_text_tool import find_service_by_text_tool
from app.agents.formatters.catalog_formatter import format_catalog_for_whatsapp
from app.services.service_selector import ServiceSelector
from app.db.session import SessionLocal


def _get_last_user_message(state: RoutingState) -> str:
    messages = state.get("messages", [])
    if not messages:
        return ""
    last_message = messages[-1]
    return (last_message.get("content") or "").strip()


def _format_service_candidates(candidates: list) -> str:
    """Formatea los servicios candidatos para que el usuario elija."""
    lines = ["Encontré varios servicios que podrían ser lo que buscas:\n"]
    for i, service in enumerate(candidates, start=1):
        lines.append(f"  *{i}.* {service.name}")
    lines.append("\n¿Cuál te interesa? Responde con el número 😊")
    return "\n".join(lines)


def catalog_node(state: RoutingState) -> RoutingState:
    """
    Nodo responsable de:
    1. Resolver selección de candidatos si el usuario eligió un número
    2. Mostrar múltiples candidatos si el texto es ambiguo
    3. Resolver directamente si hay un solo match
    4. Mostrar catálogo completo si no hay match
    """
    client_name = state.get("client_name")
    shown_service_ids = state.get("shown_service_ids", [])
    service_candidates = state.get("service_candidates") or []
    user_text = _get_last_user_message(state)
    user_text_lower = user_text.strip().lower()

    db = SessionLocal()

    try:
        # 1) Hay candidatos activos y el usuario eligió un número
        if service_candidates and user_text.isdigit():
            index = int(user_text) - 1
            if 0 <= index < len(service_candidates):
                chosen_id = service_candidates[index]["id"]
                chosen_name = service_candidates[index]["name"]
                return {
                    "selected_service_id": chosen_id,
                    "service_candidates": [],
                    "response_text": (
                        f"Perfecto, has elegido *{chosen_name}* 😊\n\n"
                        "Ahora voy a buscar los horarios disponibles para ti."
                    ),
                    "intent": Intent.BOOKING,
                }
            else:
                # Número fuera de rango → repetir opciones
                lines = [f"Por favor elige un número entre *1* y *{len(service_candidates)}*:\n"]
                for i, c in enumerate(service_candidates, start=1):
                    lines.append(f"  *{i}.* {c['name']}")
                return {
                    "response_text": "\n".join(lines),
                    "intent": Intent.FINISH,
                }

        # 2) Intentar resolver el texto del usuario a servicios
        if user_text:
            matched_services = ServiceSelector.find_services_by_text(
                db=db,
                user_text=user_text_lower,
                shown_service_ids=shown_service_ids,
            )

            # Match único → directo a booking
            if len(matched_services) == 1:
                service = matched_services[0]
                return {
                    "selected_service_id": service.id,
                    "service_candidates": [],
                    "response_text": (
                        f"Perfecto, has elegido *{service.name}* 😊\n\n"
                        "Ahora voy a buscar los horarios disponibles para ti."
                    ),
                    "intent": Intent.BOOKING,
                }

            # Múltiples matches → preguntar al usuario
            if len(matched_services) > 1:
                candidates = [
                    {"id": s.id, "name": s.name}
                    for s in matched_services
                ]
                return {
                    "service_candidates": candidates,
                    "response_text": _format_service_candidates(matched_services),
                    "intent": Intent.FINISH,
                }

        # 3) Sin match → mostrar catálogo completo
        services = get_catalog_tool(db=db)
        shown_ids = [service.id for service in services]

        return {
            "response_text": format_catalog_for_whatsapp(
                services=services,
                client_name=client_name,
            ),
            "shown_service_ids": shown_ids,
            "service_candidates": [],
            "intent": Intent.FINISH,
        }

    finally:
        db.close()