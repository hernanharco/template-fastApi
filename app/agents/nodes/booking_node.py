# app/agents/nodes/booking_node.py

from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.agents.routing.intent import Intent
from app.agents.routing.state import RoutingState
from app.agents.formatters.booking_options_formatter import BookingOptionsFormatter
from app.agents.tools.get_booking_options_tool import get_booking_options_tool
from app.db.session import SessionLocal


def booking_node(state: RoutingState) -> RoutingState:
    """
    Flujo deseado:
    - usuario elige servicio
    - sistema devuelve 2 horas disponibles
    - no pide día en esta primera versión
    """

    service_id = state.get("selected_service_id")
    client_phone = state.get("client_phone")

    if not service_id:
        return {
            "response_text": "Necesito saber qué servicio quieres reservar.",
            "intent": Intent.FINISH,
        }

    if not client_phone:
        return {
            "response_text": "No pude identificar tu teléfono para continuar con la reserva.",
            "intent": Intent.FINISH,
        }

    db: Session = SessionLocal()

    try:
        target_date = date.today()

        result = get_booking_options_tool(
            db=db,
            client_phone=client_phone,
            service_id=service_id,
            target_date=target_date,
        )

        if not result.success or not result.options:
            found_result = None

            for offset in range(1, 4):
                next_date = target_date + timedelta(days=offset)

                retry_result = get_booking_options_tool(
                    db=db,
                    client_phone=client_phone,
                    service_id=service_id,
                    target_date=next_date,
                )

                if retry_result.success and retry_result.options:
                    found_result = retry_result
                    break

            if found_result:
                result = found_result
            else:
                service_name = result.service or "ese servicio"

                return {
                    "response_text": (
                        f"No encontré horarios disponibles para *{service_name}* en los próximos días.\n\n"
                        "¿Quieres que te muestre el catálogo otra vez?"
                    ),
                    "intent": Intent.FINISH,
                    "active_slots": [],
                    "selected_datetime": None,
                    "selected_collaborator_id": None,
                    "booking_confirmed": False,
                    "appointment_id": None,
                }

        active_slots = [
            {
                "option_number": option.option_number,
                "time": option.time,
                "full_datetime": option.full_datetime,
                "collaborator_id": option.collaborator_id,
            }
            for option in result.options
        ]

        message = BookingOptionsFormatter.format_options(
            service_name=result.service or "el servicio",
            date_text=result.date or target_date.strftime("%d/%m/%Y"),
            options=active_slots,
        )

        return {
            "response_text": message,
            "active_slots": active_slots,
            "selected_datetime": None,
            "selected_collaborator_id": None,
            "booking_confirmed": False,
            "appointment_id": None,
            "intent": Intent.CONFIRMATION,
        }

    finally:
        db.close()