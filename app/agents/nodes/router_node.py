from app.agents.routing.intent import Intent
from app.agents.routing.state import RoutingState


GREETINGS = {"hola", "buenas", "buenos dias", "buenas tardes", "menu", "inicio", "reiniciar"}

# Franja horaria → time_filter_node
TIME_FILTER_KEYWORDS = [
    "tarde", "noche", "temprano",
    "antes de", "después de", "despues de",
    "entre las", "a las",
    "tienes para", "hay para", "tenés para",
    "por la", "para la", "en la",
]

# Fecha/día → time_parser_node
DATE_KEYWORDS = [
    "mañana", "manana", "hoy", "pasado",
    "otro día", "otro dia", "otra fecha",
    "siguiente", "próximo", "proximo",
    "lunes", "martes", "miercoles", "miércoles", "jueves",
    "viernes", "sabado", "sábado", "domingo",
]


def _is_valid_slot_selection(user_text: str, active_slots) -> bool:
    if not user_text.isdigit():
        return False
    index = int(user_text)
    return 1 <= index <= len(active_slots)


def _is_time_filter_query(user_text: str) -> bool:
    """Detecta si el usuario pide una franja horaria específica."""
    return any(kw in user_text for kw in TIME_FILTER_KEYWORDS)


def _is_date_query(user_text: str) -> bool:
    """Detecta si el usuario pide una fecha o día diferente."""
    return any(kw in user_text for kw in DATE_KEYWORDS)


def router_node(state: RoutingState) -> RoutingState:
    messages = state.get("messages", [])
    user_text = ""

    if messages:
        user_text = (messages[-1].get("content") or "").lower().strip()

    active_slots = state.get("active_slots") or []
    selected_service_id = state.get("selected_service_id")
    booking_confirmed = state.get("booking_confirmed", False)

    # 1. Saludo o reinicio explícito → resetear TODO el contexto
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

    # 2. Cita confirmada → el usuario quiere algo más → catálogo
    if booking_confirmed:
        return {
            "intent": Intent.CATALOG,
            "booking_confirmed": False,
            "active_slots": [],
        }

    # ── Bloque: hay slots activos ─────────────────────────────────────────────

    # 3. Hay slots + franja horaria → time_filter
    #    Ej: "tienes para la tarde?", "antes de las 3"
    if active_slots and _is_time_filter_query(user_text):
        return {"intent": Intent.TIME_FILTER, "active_slots": []}

    # 4. Hay slots + fecha/día → time_parser
    #    Ej: "y mañana?", "el viernes", "otro día"
    if active_slots and _is_date_query(user_text):
        return {"intent": Intent.TIME_PARSER, "active_slots": []}

    # 5. Hay slots + número válido → confirmation
    if active_slots and _is_valid_slot_selection(user_text, active_slots):
        return {"intent": Intent.CONFIRMATION}

    # 6. Hay slots pero respuesta inválida → pedir de nuevo
    if active_slots:
        return {"intent": Intent.CONFIRMATION}

    # ── Bloque: sin slots pero hay servicio activo ────────────────────────────
    # Ocurre cuando el turno anterior limpió slots (ej: tras "otro dia")

    # 7. Sin slots + servicio + fecha/día → time_parser
    if selected_service_id and _is_date_query(user_text):
        return {"intent": Intent.TIME_PARSER}

    # 8. Sin slots + servicio + franja horaria → time_filter
    if selected_service_id and _is_time_filter_query(user_text):
        return {"intent": Intent.TIME_FILTER}

    # 9. Sin slots + servicio → booking (busca slots para la fecha actual)
    if selected_service_id:
        return {"intent": Intent.BOOKING}

    # 10. Default → catálogo
    return {"intent": Intent.CATALOG}