import json
from datetime import time, date, timedelta
from typing import Optional

from pydantic import BaseModel
from app.agents.shared.llm import get_llm
from app.agents.routing.state import RoutingState
from app.agents.routing.intent import Intent


# ─────────────────────────────────────────
# Schema de salida
# ─────────────────────────────────────────

class TimeFilterResult(BaseModel):
    mode: str  # "after" | "before" | "between" | "first" | "last" | "unknown"
    after_hour: Optional[int] = None
    before_hour: Optional[int] = None
    weekday: Optional[int] = None  # 0=lunes ... 6=domingo
    is_time_request: bool = False


# ─────────────────────────────────────────
# Detección de día de semana en texto
# ─────────────────────────────────────────

WEEKDAY_MAP = {
    "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
    "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6,
}

def _extract_weekday(text: str) -> Optional[int]:
    """Busca un día de la semana dentro del texto normalizado."""
    for name, num in WEEKDAY_MAP.items():
        if name in text:
            return num
    return None


# ─────────────────────────────────────────
# Keywords rápidos sin LLM
# ─────────────────────────────────────────

FIRST_KEYWORDS = [
    "primera hora", "lo mas temprano", "lo más temprano",
    "mas temprano", "más temprano", "primer horario", "a primera",
]

LAST_KEYWORDS = [
    "ultima hora", "última hora", "lo mas tarde", "lo más tarde",
    "al cierre", "ultimo horario", "último horario",
    "lo ultimo", "lo último",
]


def _check_keywords(text: str) -> Optional[TimeFilterResult]:
    """
    Detecta keywords de primera/última hora SIN LLM.
    También extrae el día de la semana si viene en el mismo texto.
    Ej: "jueves a última hora" → mode=last, weekday=3, is_time_request=True
    """
    normalized = text.lower().strip()
    weekday = _extract_weekday(normalized)

    for kw in FIRST_KEYWORDS:
        if kw in normalized:
            return TimeFilterResult(mode="first", is_time_request=True, weekday=weekday)
    for kw in LAST_KEYWORDS:
        if kw in normalized:
            return TimeFilterResult(mode="last", is_time_request=True, weekday=weekday)
    return None


# ─────────────────────────────────────────
# LLM async
# ─────────────────────────────────────────

SYSTEM_PROMPT = """Eres un asistente que extrae preferencias horarias y de día de mensajes en español.
Analiza el texto y responde SOLO con un JSON con esta estructura exacta, sin markdown ni texto extra:

{
  "is_time_request": true/false,
  "mode": "after" | "before" | "between" | "first" | "last" | "unknown",
  "after_hour": null o número entero en formato 24h,
  "before_hour": null o número entero en formato 24h,
  "weekday": null o número 0=lunes,1=martes,2=miércoles,3=jueves,4=viernes,5=sábado,6=domingo
}

Reglas estrictas:
- "después de las 3" → is_time_request: true, mode: "after", after_hour: 15
- "antes de las 12" → is_time_request: true, mode: "before", before_hour: 12
- "entre las 2 y las 5" → is_time_request: true, mode: "between", after_hour: 14, before_hour: 17
- "a primera hora" → is_time_request: true, mode: "first"
- "última hora" o "lo más tarde" → is_time_request: true, mode: "last"
- Si menciona un día de la semana → extrae weekday (ej: "viernes" → 4)
- Si combina día Y preferencia horaria → is_time_request: true, incluye weekday Y el campo horario
  Ej: "el lunes antes de las 12" → is_time_request: true, mode: "before", before_hour: 12, weekday: 0
  Ej: "el viernes después de las 3" → is_time_request: true, mode: "after", after_hour: 15, weekday: 4
- IMPORTANTE: si hay cualquier referencia a hora (antes, después, entre, primera, última) → is_time_request SIEMPRE es true
- Si menciona SOLO un día sin ninguna referencia horaria → is_time_request: false, weekday: número del día
- Usa siempre formato 24h. Si el usuario dice "3" o "las 3" sin AM/PM, asume 15:00"""


async def _parse_with_llm(user_text: str) -> TimeFilterResult:
    llm = get_llm(temperature=0.0)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]
    response = await llm.ainvoke(messages)
    raw = response.content.strip().replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)
    result = TimeFilterResult(**data)

    # Salvaguarda: si hay modo horario real pero is_time_request=False, corregir
    has_hour_info = (
        result.mode in ("after", "before", "between", "first", "last")
        and result.mode != "unknown"
    )
    if has_hour_info and not result.is_time_request:
        result = result.model_copy(update={"is_time_request": True})

    return result


# ─────────────────────────────────────────
# Función pública principal (async)
# ─────────────────────────────────────────

async def parse_time_filter(user_text: str) -> TimeFilterResult:
    """
    Interpreta una preferencia horaria del usuario.
    Capa 1: keywords exactos (sin LLM) — también extrae día de semana.
    Capa 2: LLM async como fallback.
    """
    result = _check_keywords(user_text)
    if result:
        print(f"⏱ TIME FILTER (keyword): {user_text!r} → {result}")
        return result

    try:
        result = await _parse_with_llm(user_text)
        print(f"⏱ TIME FILTER (llm): {user_text!r} → {result}")
        return result
    except Exception as e:
        print(f"⚠️ TIME FILTER error: {e}")
        return TimeFilterResult(mode="unknown", is_time_request=False)


# ─────────────────────────────────────────
# Aplicar filtro sobre lista de slots
# ─────────────────────────────────────────

def apply_time_filter(slots: list, filter_result: TimeFilterResult) -> list:
    """
    Filtra active_slots según la preferencia horaria.
    Devuelve lista vacía si no hay coincidencias — el llamador maneja ese caso.
    """
    if not filter_result.is_time_request or filter_result.mode == "unknown":
        return slots

    def get_hour(slot) -> int:
        raw = slot.get("time") or slot.get("hora") if isinstance(slot, dict) else getattr(slot, "time", None)
        if isinstance(raw, str):
            return int(raw.split(":")[0])
        if isinstance(raw, time):
            return raw.hour
        return 0

    mode = filter_result.mode

    if mode == "first":
        return [min(slots, key=get_hour)] if slots else []

    if mode == "last":
        return [max(slots, key=get_hour)] if slots else []

    if mode == "after" and filter_result.after_hour is not None:
        return [s for s in slots if get_hour(s) >= filter_result.after_hour]

    if mode == "before" and filter_result.before_hour is not None:
        return [s for s in slots if get_hour(s) < filter_result.before_hour]

    if mode == "between" and filter_result.after_hour and filter_result.before_hour:
        return [s for s in slots if filter_result.after_hour <= get_hour(s) < filter_result.before_hour]

    return slots


# ─────────────────────────────────────────
# Nodo LangGraph (async)
# ─────────────────────────────────────────

async def time_filter_node(state: RoutingState) -> dict:
    messages = state.get("messages", [])
    user_text = (messages[-1].get("content") or "").strip() if messages else ""

    result = await parse_time_filter(user_text)

    # Calcular selected_date desde weekday si el LLM/keyword lo extrajo
    selected_date = state.get("selected_date")
    if result.weekday is not None:
        today = date.today()
        days_ahead = (result.weekday - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7  # si es hoy, ir a la próxima semana
        selected_date = today + timedelta(days=days_ahead)

    if not result.is_time_request:
        # Solo día sin hora → ir a booking con la fecha, sin filtro horario
        return {
            "time_filter": None,
            "selected_date": selected_date,
            "active_slots": [],
            "intent": Intent.BOOKING,
        }

    # Tiene preferencia horaria → guardar filtro y fecha, ir a booking
    return {
        "time_filter": result.model_dump(),
        "selected_date": selected_date,
        "active_slots": [],
        "intent": Intent.BOOKING,
    }