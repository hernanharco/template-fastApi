# app/agents/nodes/favorite_fallback_node.py

from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.agents.routing.intent import Intent
from app.agents.routing.state import RoutingState
from app.db.session import SessionLocal
from app.models.collaborators import Collaborator
from app.services.availability import get_available_slots

MAX_DAYS_AHEAD = 14
SLOTS_PER_BLOCK = 2


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────


def _get_collaborator_name(db: Session, collaborator_id: int) -> str:
    colab = db.query(Collaborator).filter(Collaborator.id == collaborator_id).first()
    return colab.name if colab else f"colaborador #{collaborator_id}"


def _find_next_slots_for_collaborator(
    db: Session,
    collaborator_id: int,
    service_id: int,
    from_date: date,
) -> Optional[tuple[date, list[dict]]]:
    """
    Primer día con disponibilidad para el colaborador específico.
    Devuelve (fecha, raw_slots) o None.
    """
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


def _find_general_slots_today(
    db: Session,
    service_id: int,
    target_date: date,
    exclude_collaborator_id: int,
) -> list[dict]:
    """
    Slots de CUALQUIER colaborador en target_date, excluyendo al favorito
    para evitar duplicados entre los dos bloques.
    Llama directamente a get_available_slots sin collaborator_id para
    obtener resultados generales (bypasa la lógica de favoritos).
    """
    all_slots = get_available_slots(
        db=db,
        target_date=target_date,
        service_id=service_id,
        # Sin collaborator_id → devuelve todos los colaboradores
    )
    return [s for s in all_slots if s["collaborator_id"] != exclude_collaborator_id]


def _format_slots(slots: list[dict], start_number: int) -> list[dict]:
    """Convierte raw slots al formato de active_slots del estado."""
    return [
        {
            "option_number": start_number + i,
            "time": s["start_time"].strftime("%H:%M"),
            "full_datetime": s["start_time"].strftime("%Y-%m-%d %H:%M"),
            "collaborator_id": s["collaborator_id"],
        }
        for i, s in enumerate(slots[:SLOTS_PER_BLOCK])
    ]


def _build_message(
    colab_name: str,
    original_date_label: str,
    fav_block: Optional[tuple[date, list[dict]]],
    gen_slots: list[dict],
) -> tuple[str, list[dict]]:
    """
    Construye el mensaje combinado con numeración global continua.
    Devuelve (message, active_slots).
    """
    lines = [f"*{colab_name}* no tiene disponibilidad el *{original_date_label}* 😕\n"]
    active_slots: list[dict] = []
    counter = 1

    # ── Bloque A: próximo día con el favorito ─────────────────────────
    if fav_block:
        fav_date, fav_raw = fav_block
        fav_date_label = fav_date.strftime("%d/%m/%Y")
        fav_formatted = _format_slots(fav_raw, start_number=counter)

        lines.append(f"📅 *Con {colab_name}* — próxima disponibilidad el *{fav_date_label}*:")
        for s in fav_formatted:
            lines.append(f"  *{s['option_number']}.* {s['time']}")
        lines.append("")
        active_slots.extend(fav_formatted)
        counter += len(fav_formatted)

    # ── Bloque B: cualquier profesional en la fecha original ──────────
    if gen_slots:
        gen_formatted = _format_slots(gen_slots, start_number=counter)
        original_date_label_short = original_date_label  # misma fecha pedida por el usuario

        lines.append(f"👥 *Cualquier profesional* — disponible el *{original_date_label_short}*:")
        for s in gen_formatted:
            lines.append(f"  *{s['option_number']}.* {s['time']}")
        lines.append("")
        active_slots.extend(gen_formatted)

    # ── Sin ninguna opción ────────────────────────────────────────────
    if not active_slots:
        return (
            f"*{colab_name}* no tiene disponibilidad el *{original_date_label}* "
            f"y tampoco encontré otros profesionales disponibles en los próximos "
            f"{MAX_DAYS_AHEAD} días 😕\n\n"
            "¿Quieres que te muestre el catálogo de servicios otra vez?",
            [],
        )

    nums = [str(s["option_number"]) for s in active_slots]
    reply_hint = ", ".join(f"*{n}*" for n in nums[:-1]) + f" o *{nums[-1]}*"
    lines.append(f"Responde {reply_hint} para confirmar tu elección.")

    return "\n".join(lines), active_slots


# ──────────────────────────────────────────────
# NODO PRINCIPAL
# ──────────────────────────────────────────────


def favorite_fallback_node(state: RoutingState) -> RoutingState:
    """
    Se activa cuando el favorito no tiene slots en la fecha pedida.

    Muestra en un solo mensaje:
      A) Próximo día disponible con el colaborador favorito.
      B) Slots con CUALQUIER otro profesional en la fecha original.
         → llama a get_available_slots directamente (sin favoritos)
           para garantizar que el bloque B no reutilice al favorito.

    active_slots queda con numeración global continua, por lo que
    confirmation_node no necesita ningún cambio.
    """
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

    db: Session = SessionLocal()
    try:
        colab_name = _get_collaborator_name(db, favorite_id)

        fav_block = _find_next_slots_for_collaborator(
            db=db,
            collaborator_id=favorite_id,
            service_id=service_id,
            from_date=target_date,
        )

        gen_slots = _find_general_slots_today(
            db=db,
            service_id=service_id,
            target_date=target_date,
            exclude_collaborator_id=favorite_id,
        )

        print(f"🔍 FAV_BLOCK: {fav_block}")
        print(f"🔍 GEN_SLOTS count: {len(gen_slots)}")

        message, active_slots = _build_message(
            colab_name=colab_name,
            original_date_label=original_date_label,
            fav_block=fav_block,
            gen_slots=gen_slots,
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