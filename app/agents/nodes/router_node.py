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

    # 1. Saludo o reinicio explícito: resetear TODO el contexto
    if user_text in GREETINGS or user_text in {"hi", "hello"}:
        return {
            "intent": Intent.GREETING,
            "active_slots": [],
            "selected_date": None,       # ← limpia fecha de conversación anterior
            "time_filter": None,         # ← limpia filtro horario anterior
            "selected_datetime": None,
            "selected_service_id": None,
            "booking_confirmed": False,
        }

    # 2. Si hay slots activos → siempre va a confirmation_node
    #    (tanto si elige 1/2 como si pide otro día o preferencia horaria)
    if active_slots:
        return {"intent": Intent.CONFIRMATION}

    # 3. Si hay servicio elegido pero sin slots → seguimos en booking
    if selected_service_id:
        return {"intent": Intent.BOOKING}

    # 4. Default
    return {"intent": Intent.CATALOG}