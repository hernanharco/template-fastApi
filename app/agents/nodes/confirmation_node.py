from datetime import date, timedelta
from sqlalchemy.orm import Session
from rich import print as rprint

from app.agents.routing.intent import Intent
from app.agents.routing.state import RoutingState
from app.services.booking_scheduler import confirm_booking_option
from app.db.session import SessionLocal
from app.agents.nodes.time_parser_node import parse_time_request
from app.agents.nodes.time_filter_node import parse_time_filter


# Mapeo de números escritos en español a dígitos
WORD_TO_NUMBER = {
    "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4,
    "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
    "diez": 10, "once": 11, "doce": 12, "trece": 13,
    "catorce": 14, "quince": 15, "dieciséis": 16, "diecisiete": 17,
    "dieciocho": 18, "diecinueve": 19, "veinte": 20,
}


def _normalize_hour(text: str) -> int | None:
    """
    Intenta extraer una hora del texto del usuario.
    Soporta: "10", "10.00", "10:00", "las 10", "a las 10", "las diez", "diez"
    Devuelve la hora como entero (0-23) o None si no se puede parsear.
    """
    import re
    normalized = text.lower().strip()

    # Quitar prefijos comunes: "a las", "las", "a"
    normalized = re.sub(r"^(a las|las|a)\s+", "", normalized)

    # Número en palabras
    for word, num in WORD_TO_NUMBER.items():
        if normalized == word:
            return num

    # Número con separadores: "10:00", "10.00", "10 00"
    match = re.match(r"^(\d{1,2})[:.h\s](\d{2})$", normalized)
    if match:
        return int(match.group(1))

    # Solo número: "10", "15"
    match = re.match(r"^(\d{1,2})$", normalized)
    if match:
        hour = int(match.group(1))
        if 0 <= hour <= 23:
            return hour

    return None


def _match_slot_by_hour(user_text: str, active_slots: list) -> dict | None:
    """
    Busca en active_slots el slot cuya hora coincide con lo que escribió el usuario.
    Devuelve el slot si hay coincidencia única, None si no hay o hay ambigüedad.
    """
    hour = _normalize_hour(user_text)
    if hour is None:
        return None

    matches = [
        s for s in active_slots
        if int(s["time"].split(":")[0]) == hour
    ]

    if len(matches) == 1:
        return matches[0]
    return None


def _get_last_user_message(state: RoutingState) -> str:
    messages = state.get("messages", [])
    if not messages:
        return ""
    last = messages[-1]
    return (last.get("content") or "").strip()


def _weekday_to_date(weekday: int) -> date:
    """Calcula la próxima fecha para el día de semana dado (0=lunes...6=domingo)."""
    today = date.today()
    days_ahead = (weekday - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7  # si es hoy, ir a la próxima semana
    return today + timedelta(days=days_ahead)


async def confirmation_node(state: RoutingState) -> RoutingState:
    """
    Nodo que confirma la cita cuando el usuario responde 1 o 2.
    Si el usuario pide otro día → time_parser → booking.
    Si el usuario pide preferencia horaria → time_filter_node → booking.
    """
    rprint("[bold red]🔴 CONFIRMATION NODE EJECUTADO[/bold red]")

    user_text = _get_last_user_message(state)
    active_slots = state.get("active_slots", [])
    service_id = state.get("selected_service_id")
    client_phone = state.get("client_phone")

    # ── Intentar selección por hora (ej: "10.00", "las diez", "10") ─────────
    slot_by_hour = _match_slot_by_hour(user_text, active_slots)
    if slot_by_hour:
        # Tratar como si el usuario hubiera escrito el número de opción
        user_text = str(slot_by_hour["option_number"])

    if user_text not in ["1", "2"]:

        # Capa 1: ¿es preferencia horaria?
        # Solo si time_filter no fue ya procesado en este turno
        already_filtered = state.get("time_filter") is not None
        if not already_filtered:
            time_filter_result = await parse_time_filter(user_text)
            rprint(f"[bold magenta]⏱ TIME FILTER[/bold magenta] user_text: [yellow]{user_text}[/yellow]")
            rprint(f"[bold magenta]⏱ TIME FILTER[/bold magenta] result: [yellow]{time_filter_result}[/yellow]")

            if time_filter_result.is_time_request:
                # Calcular selected_date aquí mismo si viene un weekday
                # así time_filter_node solo necesita confirmar, no recalcular
                selected_date = state.get("selected_date")
                if time_filter_result.weekday is not None:
                    selected_date = _weekday_to_date(time_filter_result.weekday)

                return {
                    "time_filter": time_filter_result.model_dump(),
                    "selected_date": selected_date,
                    "active_slots": [],
                    "intent": Intent.TIME_FILTER,
                }

        # Capa 2: ¿es petición de otro día? (mañana, el martes, etc.)
        time_result = parse_time_request(user_text)
        rprint(f"[bold cyan]⏱ TIME PARSER[/bold cyan] user_text: [yellow]{user_text}[/yellow]")
        rprint(f"[bold cyan]⏱ TIME PARSER[/bold cyan] result: [yellow]{time_result}[/yellow]")

        if time_result.get("needs_date") and time_result.get("target_date"):
            return {
                "selected_date": time_result["target_date"],
                "active_slots": [],
                "intent": Intent.BOOKING,
            }

        if time_result.get("clarification_needed"):
            return {
                "response_text": "¿Para qué día te gustaría? Por ejemplo: mañana, el lunes, el martes...",
                "intent": Intent.CONFIRMATION,
            }

        # No es número, ni fecha, ni horario → pedir que elija
        return {
            "response_text": "Por favor responde con *1* o *2* para elegir tu horario.",
            "intent": Intent.CONFIRMATION,
        }

    # ── Flujo normal: usuario eligió 1 o 2 ──────────────────────────────────

    selected_option = int(user_text)
    selected_slot = next(
        (s for s in active_slots if s["option_number"] == selected_option), None
    )

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
                "response_text": result.get("error", "No pude confirmar la cita. Intentemos nuevamente."),
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