from sqlalchemy.orm import Session

from app.agents.routing.intent import Intent
from app.agents.routing.state import RoutingState
from app.services.booking_scheduler import confirm_booking_option
from app.db.session import SessionLocal


def _get_last_user_message(state: RoutingState) -> str:
    """
    Obtiene el último mensaje del usuario desde el estado.
    """
    messages = state.get("messages", [])

    if not messages:
        return ""

    last = messages[-1]
    return (last.get("content") or "").strip()


async def confirmation_node(state: RoutingState) -> RoutingState:
    """
    Nodo que confirma la cita cuando el usuario responde 1 o 2.
    """

    user_text = _get_last_user_message(state)

    active_slots = state.get("active_slots", [])
    service_id = state.get("selected_service_id")
    client_phone = state.get("client_phone")

    # Validar entrada
    if user_text not in ["1", "2"]:
        return {
            "response_text": "Por favor responde con *1* o *2* para elegir tu horario.",
            "intent": Intent.CONFIRMATION,
        }

    selected_option = int(user_text)

    selected_slot = None
    for slot in active_slots:
        if slot["option_number"] == selected_option:
            selected_slot = slot
            break

    if not selected_slot:
        return {
            "response_text": "La opción seleccionada no es válida. Responde con *1* o *2*.",
            "intent": Intent.CONFIRMATION,
        }

    collaborator_id = selected_slot["collaborator_id"]
    selected_datetime = selected_slot["full_datetime"]

    db: Session = SessionLocal()

    try:
        result = await confirm_booking_option(
            db=db,
            client_phone=client_phone,
            service_id=service_id,
            collaborator_id=collaborator_id,
            selected_datetime=selected_datetime,
        )

        if not result.get("success"):
            return {
                "response_text": result.get(
                    "error",
                    "No pude confirmar la cita. Intentemos nuevamente.",
                ),
                "intent": Intent.FINISH,
            }

        appointment = result.get("appointment", {})

        return {
            "response_text": result.get("message"),
            "appointment_id": appointment.get("id"),
            "selected_datetime": selected_datetime,
            "selected_collaborator_id": collaborator_id,
            "booking_confirmed": True,
            "active_slots": [],
            "intent": Intent.FINISH,
        }

    finally:
        db.close()