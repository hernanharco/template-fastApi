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

    # 1. Saludo o reinicio explícito: resetear contexto pendiente
    if user_text in GREETINGS:
        return {
            "intent": Intent.GREETING,
            "active_slots": [],
            "selected_datetime": None,
            "selected_service_id": None,
            "booking_confirmed": False,
        }

    # 2. Si hay slots activos y el usuario eligió una opción válida
    if active_slots and _is_valid_slot_selection(user_text, active_slots):
        return {"intent": Intent.CONFIRMATION}

    # 3. Si hay servicio ya elegido, seguimos en booking
    if selected_service_id:
        return {"intent": Intent.BOOKING}

    # 4. Si hay slots activos pero no respondió con una opción válida,
    # mantenemos confirmación para que el nodo pida 1 o 2
    if active_slots:
        return {"intent": Intent.CONFIRMATION}

    # 5. Greeting básico
    if user_text in {"hi", "hello"}:
        return {"intent": Intent.GREETING}

    # 6. Default
    return {"intent": Intent.CATALOG}