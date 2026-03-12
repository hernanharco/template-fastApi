from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.agents.routing.intent import Intent
from app.agents.routing.state import RoutingState
from app.agents.nodes.time_filter_node import TimeFilterResult
from app.agents.utils.time_filter_utils import extract_hour_range
from app.db.session import SessionLocal
from app.models.collaborators import Collaborator
from app.models.services import Service
from app.services.availability import get_available_slots

MAX_DAYS_AHEAD = 14
SLOTS_PER_BLOCK = 2


def _get_collaborator_name(db: Session, collaborator_id: int) -> str:
    colab = db.query(Collaborator).filter(Collaborator.id == collaborator_id).first()
    return colab.name if colab else f"colaborador #{collaborator_id}"


def _find_next_slots_for_collaborator(
    db: Session,
    collaborator_id: int,
    service_id: int,
    from_date: date,
) -> Optional[tuple[date, list[dict]]]:
    for offset in range(1, MAX_DAYS_AHEAD + 1):
        candidate = from_date + timedelta(days=offset)
        slots = get_available_slots(
            db=db,
            target_date=candidate,
            service_id=service_id,
            collaborator_id=collaborator_id,
        )
        if slots:
            return candidate, slots
    return None


def _find_general_slots(
    db: Session,
    service_id: int,
    from_date: date,
    exclude_collaborator_id: int,
    max_days: int = MAX_DAYS_AHEAD,
    min_hour: Optional[int] = None,
    max_hour: Optional[int] = None,
    mode: Optional[str] = None,
) -> Optional[tuple[date, list[dict]]]:
    for offset in range(0, max_days + 1):
        candidate = from_date + timedelta(days=offset)
        all_slots = get_available_slots(
            db=db,
            target_date=candidate,
            service_id=service_id,
        )
        slots = [s for s in all_slots if s["collaborator_id"] != exclude_collaborator_id]

        if min_hour is not None:
            slots = [s for s in slots if s["start_time"].hour >= min_hour]
        if max_hour is not None:
            slots = [s for s in slots if s["start_time"].hour < max_hour]

        if slots and mode == "first":
            slots = [min(slots, key=lambda s: s["start_time"].hour)]
        elif slots and mode == "last":
            slots = [max(slots, key=lambda s: s["start_time"].hour)]

        if slots:
            return candidate, slots
    return None


def _format_slots(slots: list[dict], start_number: int) -> list[dict]:
    return [
        {
            "option_number": start_number + i,
            "time": s["start_time"].strftime("%H:%M"),
            "full_datetime": s["start_time"].strftime("%Y-%m-%d %H:%M"),
            "collaborator_id": s["collaborator_id"],
        }
        for i, s in enumerate(slots[:SLOTS_PER_BLOCK])
    ]


def _build_reply_hint(active_slots: list[dict]) -> str:
    """Construye el texto de respuesta según cantidad de opciones."""  # ← NUEVO helper
    nums = [str(s["option_number"]) for s in active_slots]
    if len(nums) == 1:
        return f"*{nums[0]}*"
    return ", ".join(f"*{n}*" for n in nums[:-1]) + f" o *{nums[-1]}*"


def _build_message(
    colab_name: str,
    original_date_label: str,
    fav_block: Optional[tuple[date, list[dict]]],
    gen_block: Optional[tuple[date, list[dict]]],
    service_name: str = "el servicio",
) -> tuple[str, list[dict]]:
    lines = [f"*{colab_name}* no tiene disponibilidad el *{original_date_label}* 😕\n"]
    active_slots: list[dict] = []
    counter = 1

    if fav_block:
        fav_date, fav_raw = fav_block
        fav_formatted = _format_slots(fav_raw, start_number=counter)
        lines.append(f"📅 *Con {colab_name}* — próxima disponibilidad el *{fav_date.strftime('%d/%m/%Y')}*:")
        for s in fav_formatted:
            lines.append(f"  *{s['option_number']}.* {s['time']}")
        lines.append("")
        active_slots.extend(fav_formatted)
        counter += len(fav_formatted)

    if gen_block:
        gen_date, gen_raw = gen_block
        gen_formatted = _format_slots(gen_raw, start_number=counter)
        gen_date_label = gen_date.strftime("%d/%m/%Y")
        suffix = original_date_label if gen_date_label == original_date_label else gen_date_label
        lines.append(f"👥 *Cualquier profesional* — disponible el *{suffix}*:")
        for s in gen_formatted:
            lines.append(f"  *{s['option_number']}.* {s['time']}")
        lines.append("")
        active_slots.extend(gen_formatted)

    if not active_slots:
        return (
            f"*{colab_name}* no tiene disponibilidad el *{original_date_label}* "
            f"y tampoco encontré otros profesionales disponibles en los próximos "
            f"{MAX_DAYS_AHEAD} días 😕\n\n"
            "¿Quieres que te muestre el catálogo de servicios otra vez?",
            [],
        )

    reply_hint = _build_reply_hint(active_slots)  # ← usa helper, sin bug
    lines.append(f"Responde {reply_hint} para confirmar tu elección.")

    if not fav_block and gen_block:
        gen_date, _ = gen_block
        clean_lines = [f"👥 Tengo estas opciones disponibles para *{service_name}* el *{gen_date.strftime('%d/%m/%Y')}*:\n"]
        for s in active_slots:
            clean_lines.append(f"  *{s['option_number']}.* {s['time']}")
        clean_lines.append(f"\nResponde {reply_hint} para confirmar tu elección.")
        return "\n".join(clean_lines), active_slots

    return "\n".join(lines), active_slots


def favorite_fallback_node(state: RoutingState) -> RoutingState:
    service_id = state.get("selected_service_id")
    client_phone = state.get("client_phone")
    preferred = state.get("preferred_collaborators") or []
    target_date = state.get("selected_date") or date.today()

    if not service_id or not preferred:
        return {
            "response_text": "Algo salió mal al buscar tu colaborador favorito. ¿Intentamos de nuevo?",
            "intent": Intent.FINISH,
        }

    favorite_id = preferred[0]
    original_date_label = target_date.strftime("%d/%m/%Y")

    time_filter_data = state.get("time_filter")
    filter_result = TimeFilterResult(**time_filter_data) if time_filter_data else None
    min_hour, max_hour = extract_hour_range(filter_result) if filter_result else (None, None)
    filter_mode = filter_result.mode if filter_result else None

    db: Session = SessionLocal()
    try:
        colab_name = _get_collaborator_name(db, favorite_id)
        service = db.query(Service).filter(Service.id == service_id, Service.is_active == True).first()
        service_name = service.name if service else "el servicio"

        fav_block = _find_next_slots_for_collaborator(
            db=db,
            collaborator_id=favorite_id,
            service_id=service_id,
            from_date=target_date,
        )

        gen_block = _find_general_slots(
            db=db,
            service_id=service_id,
            from_date=target_date,
            exclude_collaborator_id=favorite_id,
            min_hour=min_hour,
            max_hour=max_hour,
            mode=filter_mode,
        )

        print(f"🔍 FAV_BLOCK: {fav_block}")
        print(f"🔍 GEN_BLOCK: {gen_block[0] if gen_block else None}, slots: {len(gen_block[1]) if gen_block else 0}")

        message, active_slots = _build_message(
            colab_name=colab_name,
            original_date_label=original_date_label,
            fav_block=fav_block,
            gen_block=gen_block,
            service_name=service_name,
        )

        intent = Intent.FINISH if not active_slots else Intent.CONFIRMATION

        return {
            "response_text": message,
            "active_slots": active_slots,
            "next_action": "favorite_fallback_pending" if active_slots else None,
            "selected_date": target_date,
            "selected_datetime": None,
            "selected_collaborator_id": None,
            "booking_confirmed": False,
            "appointment_id": None,
            "intent": intent,
        }

    finally:
        db.close()