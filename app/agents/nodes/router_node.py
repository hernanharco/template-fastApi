from app.agents.routing.intent import Intent
from app.agents.routing.state import RoutingState


GREETINGS = {"hola", "buenas", "buenos dias", "buenas tardes", "menu", "inicio", "reiniciar"}


def _is_valid_slot_selection(user_text: str, active_slots) -> bool:
    if not user_text.isdigit():
        return False
    index = int(user_text)
    return 1 <= index <= len(active_slots)


def router_node(state: RoutingState) -> RoutingState:
    messages = state.get("messages", [])
    user_text = ""

    if messages:
        user_text = (messages[-1].get("content") or "").lower().strip()

    active_slots = state.get("active_slots") or []
    selected_service_id = state.get("selected_service_id")
    booking_confirmed = state.get("booking_confirmed", False)

    # 1. Saludo o reinicio explícito: resetear TODO el contexto
    if user_text in GREETINGS or user_text in {"hi", "hello"}:
        return {
            "intent": Intent.GREETING,
            "active_slots": [],
            "selected_date": None,
            "time_filter": None,
            "selected_datetime": None,
            "selected_service_id": None,
            "booking_confirmed": False,
        }

    # 2. Si la cita ya fue confirmada → el usuario quiere algo más → catálogo
    #    (selected_service_id ya fue limpiado en finish_node)
    if booking_confirmed:
        return {
            "intent": Intent.CATALOG,
            "booking_confirmed": False,
            "active_slots": [],
        }

    # 3. Si hay slots activos → siempre va a confirmation_node
    if active_slots:
        return {"intent": Intent.CONFIRMATION}

    # 4. Si hay servicio elegido pero sin slots → seguimos en booking
    if selected_service_id:
        return {"intent": Intent.BOOKING}

    # 5. Default
    return {"intent": Intent.CATALOG}