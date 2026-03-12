from datetime import date, timedelta
from typing import Optional
import json

from pydantic import BaseModel
from rich import print as rprint

from app.agents.routing.state import RoutingState
from app.agents.routing.intent import Intent
from app.agents.shared.llm import get_llm
from app.agents.nodes.time_filter_node import parse_time_filter  # ← NUEVO


class ParsedDate(BaseModel):
    target_date: Optional[str] = None
    needs_date: bool = False
    clarification_needed: bool = False


OTRO_DIA_KEYWORDS = {
    "otro dia", "otro día", "otra fecha", "otra hora",
    "diferente dia", "diferente día", "cambia el dia",
    "no ese dia", "no ese día", "otro momento",
    "a otra hora", "en otro horario", "otro horario",
    "a esa hora no", "a esas horas no", "esa hora no",
    "no a esa hora", "no me viene esa hora",
    "no puedo a esa hora", "no puedo ese dia", "no puedo ese día",
}

WEEKDAY_NAMES = {
    "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
    "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6,
}

RELATIVE_DAYS = {
    "pasado mañana": 2,
    "mañana": 1,
    "hoy": 0,
    "pasado": 2,
}


def _next_weekday(weekday: int) -> date:
    today = date.today()
    days_ahead = weekday - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


def _extract_weekday(text: str) -> Optional[int]:
    for day_name, day_num in WEEKDAY_NAMES.items():
        if day_name in text:
            return day_num
    return None


def parse_time_request(user_text: str) -> dict:
    normalized = user_text.lower().strip()

    if normalized in OTRO_DIA_KEYWORDS:
        return {"needs_date": True, "target_date": None, "clarification_needed": True}

    for phrase, offset in RELATIVE_DAYS.items():
        if phrase in normalized:
            target = date.today() + timedelta(days=offset)
            return {"needs_date": True, "target_date": target, "clarification_needed": False}

    weekday = _extract_weekday(normalized)
    if weekday is not None:
        target = _next_weekday(weekday)
        return {"needs_date": True, "target_date": target, "clarification_needed": False}

    today = date.today()
    tomorrow = (today + timedelta(days=1)).isoformat()

    prompt = f"""
Hoy es {today.strftime('%A %d de %B de %Y')} ({today.isoformat()}).
El usuario está agendando una cita y dice: "{user_text}"

Determina si el usuario está pidiendo una fecha diferente para su cita.
Responde SOLO con JSON, sin markdown, sin explicación:

{{
  "target_date": "YYYY-MM-DD o null si no pide fecha específica",
  "needs_date": true o false (true si el usuario quiere otro día),
  "clarification_needed": true o false
}}

Ejemplos:
- "el 15 de marzo" → target_date: "2026-03-15", needs_date: true
- "1" o "2" → el usuario elige slot, needs_date: false
- "para las 3" → needs_date: true, clarification_needed: true, target_date: null
- "sí" / "confirmo" → needs_date: false
- "mañana a las 3" → target_date: "{tomorrow}", needs_date: true
"""

    try:
        llm = get_llm()
        response = llm.invoke(prompt)
        raw = response.content.strip()
        parsed = json.loads(raw)

        if parsed.get("needs_date") and parsed.get("target_date"):
            parsed["target_date"] = date.fromisoformat(parsed["target_date"])

        return parsed

    except Exception:
        return {"needs_date": False, "target_date": None, "clarification_needed": False}


async def time_parser_node(state: RoutingState) -> RoutingState:  # ← async
    selected_service_id = state.get("selected_service_id")
    last_message = state.get("messages", [])

    if not selected_service_id:
        return {"intent": Intent.BOOKING}

    if not last_message:
        return {"intent": Intent.BOOKING}

    user_text = (
        last_message[-1].get("content", "")
        if isinstance(last_message[-1], dict)
        else str(last_message[-1])
    )

    result = parse_time_request(user_text)

    rprint(f"[bold cyan]⏱ TIME PARSER[/bold cyan] user_text: [yellow]{user_text}[/yellow]")
    rprint(f"[bold cyan]⏱ TIME PARSER[/bold cyan] result: [yellow]{result}[/yellow]")

    if result.get("needs_date") and result.get("target_date"):
        # ← NUEVO: detectar filtro horario en el mismo mensaje
        try:
            filter_result = await parse_time_filter(user_text)
            time_filter_data = filter_result.model_dump() if filter_result.is_time_request else None
        except Exception:
            time_filter_data = None

        rprint(f"[bold cyan]⏱ TIME PARSER[/bold cyan] time_filter: [yellow]{time_filter_data}[/yellow]")

        return {
            "selected_date": result["target_date"],
            "active_slots": [],
            "time_filter": time_filter_data,  # ← NUEVO
            "intent": Intent.BOOKING,
        }

    if result.get("clarification_needed"):
        return {
            "response_text": "¿Para qué día o a qué hora te vendría mejor? Por ejemplo: mañana, el lunes, después de las 3...",
            "intent": Intent.FINISH,
        }

    return {"intent": Intent.BOOKING}
# ```

# El único cambio real son 10 líneas — el resto del archivo es idéntico. Cuando pruebes con "para el viernes despues de las tres" deberías ver en los logs:
# ```
# ⏱ TIME PARSER result: {'needs_date': True, 'target_date': datetime.date(2026, 3, 13), ...}
# ⏱ TIME PARSER time_filter: {'mode': 'after', 'after_hour': 15, 'is_time_request': True, ...}