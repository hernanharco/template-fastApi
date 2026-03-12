from app.agents.routing.intent import Intent
from app.agents.routing.state import RoutingState


GREETINGS = {"hola", "buenas", "buenos dias", "buenas tardes", "menu", "inicio", "reiniciar"}

FAREWELL_KEYWORDS = {
    "gracias", "muchas gracias", "ok gracias", "listo gracias",
    "hasta luego", "hasta pronto", "nos vemos", "chao", "chau",
    "bye", "adios", "adiós", "hasta mañana", "hasta manana",
    "perfecto gracias", "de acuerdo gracias", "genial gracias",
    "todo bien gracias", "excelente gracias", "listo muchas gracias",
}

MODIFICATION_KEYWORDS = [                                          # ← NUEVO
    "cancelar", "cancel", "cancelar cita", "anular",
    "modificar", "cambiar cita", "cambiar mi cita",
    "reprogramar", "mover la cita", "mover mi cita",
    "eliminar cita", "borrar cita", "quiero cancelar",
    "quiero modificar", "quiero cambiar mi cita",
]

TIME_FILTER_KEYWORDS = [
    "tarde", "noche", "temprano",
    "antes de", "después de", "despues de",
    "entre las", "a las",
    "tienes para", "hay para", "tenés para",
    "por la", "para la", "en la",
    "ultima hora", "última hora",
    "primer hora", "primera hora",
    "a ultima", "a última",
    "a primera",
]

DATE_KEYWORDS = [
    "mañana", "manana", "hoy", "pasado",
    "otro día", "otro dia", "otra fecha",
    "siguiente", "próximo", "proximo",
    "lunes", "martes",
    "miercoles", "miércoles",
    "jueve", "jueves",
    "viernes",
    "sabado", "sábado", "domingo",
]

SERVICE_CHANGE_KEYWORDS = [
    "cambiar de servicio", "cambiar servicio", "otro servicio",
    "hacerme otra cosa", "otra cosa", "quiero otra cosa",
    "quiero cambiar", "quiero otro", "diferente servicio",
    "ver servicios", "ver el catalogo", "ver catálogo",
    "el catalogo", "el catálogo",
]


def _is_valid_slot_selection(user_text: str, active_slots) -> bool:
    if not user_text.isdigit():
        return False
    index = int(user_text)
    return 1 <= index <= len(active_slots)


def _is_valid_candidate_selection(user_text: str, service_candidates) -> bool:
    if not user_text.isdigit():
        return False
    index = int(user_text)
    return 1 <= index <= len(service_candidates)


def _is_time_filter_query(user_text: str) -> bool:
    return any(kw in user_text for kw in TIME_FILTER_KEYWORDS)


def _is_date_query(user_text: str) -> bool:
    return any(kw in user_text for kw in DATE_KEYWORDS)


def _is_service_change(user_text: str) -> bool:
    return any(kw in user_text for kw in SERVICE_CHANGE_KEYWORDS)


def _is_farewell(user_text: str) -> bool:
    return user_text in FAREWELL_KEYWORDS or any(kw in user_text for kw in FAREWELL_KEYWORDS)


def _is_modification(user_text: str) -> bool:                     # ← NUEVO
    return any(kw in user_text for kw in MODIFICATION_KEYWORDS)


def router_node(state: RoutingState) -> RoutingState:
    messages = state.get("messages", [])
    user_text = ""

    if messages:
        user_text = (messages[-1].get("content") or "").lower().strip()

    active_slots = state.get("active_slots") or []
    service_candidates = state.get("service_candidates") or []
    selected_service_id = state.get("selected_service_id")
    booking_confirmed = state.get("booking_confirmed", False)

    # 1. Saludo o reinicio explícito
    if user_text in GREETINGS or user_text in {"hi", "hello"}:
        return {
            "intent": Intent.GREETING,
            "active_slots": [],
            "selected_date": None,
            "time_filter": None,
            "selected_datetime": None,
            "selected_service_id": None,
            "service_candidates": [],
            "booking_confirmed": False,
        }

    # 2. Despedida
    if _is_farewell(user_text):
        return {
            "intent": Intent.FAREWELL,
            "active_slots": [],
            "service_candidates": [],
        }

    # 3. Modificación o cancelación → derivar al establecimiento  # ← NUEVO
    if _is_modification(user_text):
        return {
            "intent": Intent.MODIFICATION_REQUEST,
            "active_slots": [],
            "service_candidates": [],
        }

    # 4. Esperando nombre
    if state.get("wait_for_name"):
        return {"intent": Intent.GREETING}

    # 5. Cita confirmada → catálogo
    if booking_confirmed:
        return {
            "intent": Intent.CATALOG,
            "booking_confirmed": False,
            "active_slots": [],
            "service_candidates": [],
        }

    # 6. Cambio de servicio explícito → catálogo, limpiar contexto
    if _is_service_change(user_text):
        return {
            "intent": Intent.CATALOG,
            "active_slots": [],
            "selected_service_id": None,
            "selected_date": None,
            "time_filter": None,
            "service_candidates": [],
        }

    # 7. Candidatos activos + número válido → catálogo resuelve la elección
    if service_candidates and _is_valid_candidate_selection(user_text, service_candidates):
        return {"intent": Intent.CATALOG}

    # 8. Candidatos activos pero respuesta inválida → repetir opciones
    if service_candidates:
        return {"intent": Intent.CATALOG}

    # ── Bloque: hay slots activos ─────────────────────────────────────────────

    # 9. Slots + fecha + franja → time_parser
    if active_slots and _is_date_query(user_text) and _is_time_filter_query(user_text):
        return {"intent": Intent.TIME_PARSER, "active_slots": []}

    # 10. Slots + franja horaria sola → time_filter
    if active_slots and _is_time_filter_query(user_text):
        return {"intent": Intent.TIME_FILTER, "active_slots": []}

    # 11. Slots + fecha/día sola → time_parser
    if active_slots and _is_date_query(user_text):
        return {"intent": Intent.TIME_PARSER, "active_slots": []}

    # 12. Slots + número válido → confirmation
    if active_slots and _is_valid_slot_selection(user_text, active_slots):
        return {"intent": Intent.CONFIRMATION}

    # 13. Slots pero respuesta inválida → pedir de nuevo
    if active_slots:
        return {"intent": Intent.CONFIRMATION}

    # ── Bloque: sin slots pero hay servicio activo ────────────────────────────

    # 14. Sin slots + servicio + fecha + franja → time_parser
    if selected_service_id and _is_date_query(user_text) and _is_time_filter_query(user_text):
        return {"intent": Intent.TIME_PARSER}

    # 15. Sin slots + servicio + fecha sola → time_parser
    if selected_service_id and _is_date_query(user_text):
        return {"intent": Intent.TIME_PARSER}

    # 16. Sin slots + servicio + franja sola → time_filter
    if selected_service_id and _is_time_filter_query(user_text):
        return {"intent": Intent.TIME_FILTER}

    # 17. Sin slots + servicio → booking
    if selected_service_id:
        return {"intent": Intent.BOOKING}

    # 18. Default → catálogo
    return {"intent": Intent.CATALOG}