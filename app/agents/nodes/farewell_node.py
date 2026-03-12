from app.agents.routing.intent import Intent
from app.agents.routing.state import RoutingState

FAREWELL_RESPONSES = [
    "¡Hasta pronto, {name}! 😊 Fue un placer atenderte.",
    "¡Que te vaya bien, {name}! 🌟 Aquí estaremos cuando nos necesites.",
    "¡Nos vemos, {name}! 👋 Que tengas un excelente día.",
]

import random


def farewell_node(state: RoutingState) -> RoutingState:
    client_name = state.get("client_name") or "!"
    template = random.choice(FAREWELL_RESPONSES)
    message = template.format(name=client_name)

    return {
        "response_text": message,
        "intent": Intent.FINISH,
        "active_slots": [],
        "service_candidates": [],
        "selected_service_id": None,
        "selected_date": None,
        "time_filter": None,
    }