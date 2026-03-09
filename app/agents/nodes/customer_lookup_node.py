from app.agents.routing.intent import Intent
from app.agents.routing.state import RoutingState
from app.agents.tools.ensure_client_tool import ensure_client_tool
from app.db.session import SessionLocal


def customer_lookup_node(state: RoutingState) -> RoutingState:
    """
    Busca o crea al cliente en base de datos usando su teléfono.
    Si el cliente aún tiene el nombre por defecto, marca wait_for_name=True
    para que el flujo de greeting solicite su nombre.
    """
    phone = state.get("client_phone")

    if not phone:
        return {
            "intent": Intent.FINISH,
            "response_text": "No pude identificar tu número de teléfono.",
        }

    db = SessionLocal()

    try:
        client = ensure_client_tool(phone=phone, db=db)

        needs_name = (
            not client.client_name
            or client.client_name == "Nuevo Cliente"
            or client.is_new_user
        )

        return {
            "client_id": client.client_id,
            "client_name": client.client_name,
            "preferred_collaborators": client.preferred_collaborators,
            "is_new_user": client.is_new_user,
            "wait_for_name": needs_name,
            "intent": Intent.GREETING if needs_name else Intent.CATALOG,
        }

    finally:
        db.close()