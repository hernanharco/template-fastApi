from app.agents.routing.intent import Intent
from app.agents.routing.state import RoutingState


def modification_request_node(state: RoutingState) -> RoutingState:
    """
    Nodo ejecutado cuando el usuario quiere modificar o cancelar una cita.
    En lugar de permitirlo directamente, deriva al establecimiento.

    Futuro: consultar datos de contacto del negocio desde la DB.
    """
    return {
        "response_text": (
            "Para modificar o cancelar tu cita, por favor contáctanos directamente 😊\n\n"
            "📞 Puedes llamarnos o escribirnos por este medio y con gusto te ayudamos.\n\n"
            "¡Gracias por avisarnos! 🌟"
        ),
        "intent": Intent.FINISH,
    }