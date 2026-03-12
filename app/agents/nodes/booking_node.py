from datetime import date, timedelta
from sqlalchemy.orm import Session

from app.agents.routing.intent import Intent
from app.agents.routing.state import RoutingState
from app.agents.formatters.booking_options_formatter import BookingOptionsFormatter
from app.agents.tools.get_booking_options_tool import get_booking_options_tool
from app.agents.nodes.time_filter_node import TimeFilterResult
from app.agents.utils.time_filter_utils import extract_hour_range, filter_description
from app.db.session import SessionLocal


def _apply_first_last(slots: list, mode: str) -> list:
    if not slots:
        return slots
    if mode == "first":
        return [{**slots[0], "option_number": 1}]
    if mode == "last":
        return [{**slots[-1], "option_number": 1}]
    return slots


def booking_node(state: RoutingState) -> RoutingState:

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
        target_date = state.get("selected_date") or date.today()
        preferred = state.get("preferred_collaborators") or []

        time_filter_data = state.get("time_filter")
        filter_result = TimeFilterResult(**time_filter_data) if time_filter_data else None
        min_hour, max_hour = extract_hour_range(filter_result) if filter_result else (None, None)
        filter_desc = filter_description(filter_result) if filter_result else None
        needs_all_slots = filter_result and filter_result.mode in ("first", "last")

        result = get_booking_options_tool(
            db=db,
            client_phone=client_phone,
            service_id=service_id,
            target_date=target_date,
            min_hour=min_hour,
            max_hour=max_hour,
            limit=None if needs_all_slots else 2,
        )

        # ── Favorito sin slots → delegar al nodo especializado ───────────────
        if preferred:
            favorite_got_slot = result.success and any(
                opt.collaborator_id in preferred
                for opt in (result.options or [])
            )
            if not favorite_got_slot:
                return {
                    "intent": Intent.FAVORITE_FALLBACK,
                    "selected_service_id": service_id,
                    "selected_date": target_date,
                    "client_phone": client_phone,
                    "preferred_collaborators": preferred,
                    "time_filter": time_filter_data,
                }

        # ── Sin resultados Y sin favorito: buscar en días siguientes ─────────
        if not result.success or not result.options:
            original_date_text = target_date.strftime("%d/%m/%Y")
            found_result = None
            found_date = None

            for offset in range(1, 8):
                next_date = target_date + timedelta(days=offset)
                retry_result = get_booking_options_tool(
                    db=db,
                    client_phone=client_phone,
                    service_id=service_id,
                    target_date=next_date,
                    min_hour=min_hour,
                    max_hour=max_hour,
                    limit=None if needs_all_slots else 2,
                )
                if retry_result.success and retry_result.options:
                    found_result = retry_result
                    found_date = next_date
                    break

            if found_result:
                result = found_result
                new_date_text = result.date or found_date.strftime("%d/%m/%Y")
                service_name = result.service or "el servicio"

                active_slots = [
                    {
                        "option_number": option.option_number,
                        "time": option.time,
                        "full_datetime": option.full_datetime,
                        "collaborator_id": option.collaborator_id,
                    }
                    for option in result.options
                ]

                if filter_result and filter_result.mode in ("first", "last"):
                    active_slots = _apply_first_last(active_slots, filter_result.mode)

                if filter_result:
                    message = (
                        f"El *{original_date_text}* no tengo horarios disponibles "
                        f"{filter_desc} para *{service_name}* 😕\n\n"
                        f"El próximo día disponible {filter_desc} es el *{new_date_text}*:\n\n"
                    )
                    for slot in active_slots:
                        message += f"  *{slot['option_number']}.* {slot['time']}\n"
                    reply_hint = BookingOptionsFormatter._build_reply_hint(active_slots)
                    message += f"\nResponde {reply_hint} para confirmar, o dime otro día si prefieres."
                else:
                    message = BookingOptionsFormatter.format_options(
                        service_name=service_name,
                        date_text=new_date_text,
                        options=active_slots,
                    )

                return {
                    "response_text": message,
                    "active_slots": active_slots,
                    "selected_datetime": None,
                    "selected_collaborator_id": None,
                    "booking_confirmed": False,
                    "appointment_id": None,
                    "time_filter": None,
                    "intent": Intent.CONFIRMATION,
                }
            else:
                service_name = result.service or "ese servicio"
                return {
                    "response_text": (
                        f"No encontré horarios disponibles para *{service_name}*"
                        + (f" {filter_desc}" if filter_desc else "")
                        + " en los próximos días.\n\n¿Quieres que te muestre el catálogo otra vez?"
                    ),
                    "intent": Intent.FINISH,
                    "active_slots": [],
                    "selected_datetime": None,
                    "selected_collaborator_id": None,
                    "booking_confirmed": False,
                    "appointment_id": None,
                    "time_filter": None,
                }

        # ── Slots encontrados en target_date ─────────────────────────────────
        active_slots = [
            {
                "option_number": option.option_number,
                "time": option.time,
                "full_datetime": option.full_datetime,
                "collaborator_id": option.collaborator_id,
            }
            for option in result.options
        ]

        if filter_result and filter_result.mode in ("first", "last"):
            active_slots = _apply_first_last(active_slots, filter_result.mode)

        print(f"🔍 SLOTS: {[s['time'] for s in active_slots]}")

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
            "time_filter": None,
            "intent": Intent.CONFIRMATION,
        }

    finally:
        db.close()