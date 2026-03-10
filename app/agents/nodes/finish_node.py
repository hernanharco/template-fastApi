from app.agents.routing.intent import Intent
from app.agents.routing.state import RoutingState


def finish_node(state: RoutingState) -> RoutingState:
    """
    Nodo ejecutado tras confirmar una cita exitosamente.
    Responsabilidades (SRP):
      - Adjuntar pregunta de seguimiento al mensaje de confirmación.
      - Limpiar el estado de la conversación para un nuevo ciclo.
      - Marcar intent como CATALOG para que el router sepa que
        el próximo mensaje del usuario debe ir al catálogo.
    """
    confirmation_message = state.get("response_text", "")
    follow_up = "\n\n¿Necesitas algo más? 😊"

    return {
        "response_text": confirmation_message + follow_up,
        # Limpiar estado para el próximo ciclo
        "selected_service_id": None,
        "selected_date": None,
        "time_filter": None,
        "active_slots": [],
        # booking_confirmed queda True — el router lo usa para
        # saber que el próximo mensaje va al catálogo
        "booking_confirmed": True,
        "intent": Intent.FINISH,
    }