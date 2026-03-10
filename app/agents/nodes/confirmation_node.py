from sqlalchemy.orm import Session
from rich import print as rprint

from app.agents.routing.intent import Intent
from app.agents.routing.state import RoutingState
from app.services.booking_scheduler import confirm_booking_option
from app.db.session import SessionLocal


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


async def confirmation_node(state: RoutingState) -> RoutingState:
    """
    Responsabilidad única: confirmar la cita cuando el usuario elige 1 o 2.
    Las redirecciones por fecha/franja ya las maneja el router_node antes
    de llegar aquí — este nodo solo procesa la selección del slot.
    """
    rprint("[bold red]🔴 CONFIRMATION NODE EJECUTADO[/bold red]")

    user_text = _get_last_user_message(state)
    active_slots = state.get("active_slots", [])
    service_id = state.get("selected_service_id")
    client_phone = state.get("client_phone")

    # ── Intentar selección por hora (ej: "10.00", "las diez", "10") ─────────
    slot_by_hour = _match_slot_by_hour(user_text, active_slots)
    if slot_by_hour:
        user_text = str(slot_by_hour["option_number"])

    # ── Si no es 1 ni 2 → pedir que elija ───────────────────────────────────
    # Nota: el router ya interceptó fechas y franjas horarias antes de llegar aquí
    if user_text not in ["1", "2"]:
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