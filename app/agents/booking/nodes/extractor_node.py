import re
import json
from datetime import datetime, timedelta
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# ✅ Lazy init — se crea solo cuando se necesita, no al importar
_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    return _llm


# ─────────────────────────────────────────────
# Resolución determinista en Python (sin LLM)
# ─────────────────────────────────────────────

_DIAS = {
    "lunes": 0,
    "martes": 1,
    "miércoles": 2,
    "miercoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sábado": 5,
    "sabado": 5,
    "domingo": 6,
}


def _resolver_fecha_python(msg: str, hoy_dt: datetime) -> str | None:
    """
    Resuelve fechas simples y franjas en Python puro, sin LLM.
    Devuelve 'YYYY-MM-DD' o None si no puede resolver.
    """
    msg = msg.lower().strip()
    msg = (
        msg.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )

    # Franjas: "antes del X" → día anterior a X más próximo
    antes_match = re.search(r"antes del?\s+(\w+)", msg)
    if antes_match:
        dia_nombre = antes_match.group(1)
        if dia_nombre in _DIAS:
            idx_limite = _DIAS[dia_nombre]
            # Buscamos el día justo anterior dentro de los próximos 7 días
            idx_anterior = (idx_limite - 1) % 7
            diff = (idx_anterior - hoy_dt.weekday()) % 7
            diff = diff if diff > 0 else 7
            return (hoy_dt + timedelta(days=diff)).strftime("%Y-%m-%d")

    # Franjas: "entre el X y el Y" → primer día de la franja más próximo
    entre_match = re.search(r"entre el?\s+(\w+)\s+y el?\s+(\w+)", msg)
    if entre_match:
        dia_inicio = entre_match.group(1)
        if dia_inicio in _DIAS:
            idx = _DIAS[dia_inicio]
            diff = (idx - hoy_dt.weekday()) % 7
            diff = diff if diff > 0 else 7
            return (hoy_dt + timedelta(days=diff)).strftime("%Y-%m-%d")

    # Día de la semana mencionado en cualquier parte del mensaje (prioridad alta)
    for nombre, idx in _DIAS.items():
        if nombre in msg:
            diff = (idx - hoy_dt.weekday()) % 7
            diff = diff if diff > 0 else 7
            return (hoy_dt + timedelta(days=diff)).strftime("%Y-%m-%d")

    # Fechas relativas simples (prioridad baja)
    if "pasado mañana" in msg or "pasado manana" in msg:
        return (hoy_dt + timedelta(days=2)).strftime("%Y-%m-%d")
    if "mañana" in msg or "manana" in msg:
        return (hoy_dt + timedelta(days=1)).strftime("%Y-%m-%d")
    if "hoy" in msg:
        return hoy_dt.strftime("%Y-%m-%d")

    return None


# ─────────────────────────────────────────────
# Nodo principal
# ─────────────────────────────────────────────


def extractor_node(state: dict) -> dict:
    hoy = state.get("current_date", datetime.now().strftime("%Y-%m-%d"))
    hoy_dt = datetime.strptime(hoy, "%Y-%m-%d")
    messages = state.get("messages", [])

    # 🚀 IMPORTANTE: Buscar el último mensaje del USUARIO, no el último mensaje en general
    last_user_msg = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break

    # 1. Intentar resolver en Python primero (rápido y determinista)
    fecha_py = _resolver_fecha_python(last_user_msg, hoy_dt)
    if fecha_py:
        print(f"🤖 [IA Extractor] Fecha resuelta en Python: {fecha_py}")
        return {
            "appointment_date": fecha_py,
            "appointment_time": None,
        }

    # 2. Si no se pudo, usar LLM para expresiones complejas
    # ("la semana que viene", "el primer jueves de marzo", referencias al historial)
    recent = messages[-4:] if len(messages) >= 4 else messages
    history_text = "\n".join(
        f"{'Usuario' if m['role'] == 'user' else 'Valeria'}: {m['content']}"
        for m in recent
    )

    dias_es = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    hoy_nombre = dias_es[hoy_dt.weekday()]

    system = f"""Hoy es {hoy} ({hoy_nombre}).
        Extrae fecha y hora del mensaje del usuario usando el historial como contexto.

        Historial reciente:
        {history_text}

        Reglas:
        - Resuelve expresiones de fecha relativas usando hoy ({hoy}) como referencia.
        - Si el usuario referencia algo anterior ("arriba dije hoy", "como dije antes"),
        busca la fecha en el historial y resuélvela.
        - "hoy", "mañana", días de la semana son FECHAS, nunca horas.
        - Una hora tiene formato HH:MM o expresiones como "a las 9", "las 10:30".
        - Si no hay fecha, devuelve null. Si no hay hora, devuelve null.

        FRANJAS DE TIEMPO:
        - "entre el lunes y el jueves" → elige el primer día disponible de esa franja
        (el más próximo que no haya pasado).
        - "antes del sábado" → elige el viernes más próximo.
        - "a principios de semana" → lunes más próximo.
        - "a finales de semana" → viernes más próximo.
        - Siempre resuelve la franja a UNA fecha concreta en formato YYYY-MM-DD.

        Responde ÚNICAMENTE JSON puro, sin markdown:
        {{"date": "YYYY-MM-DD", "time": "HH:MM", "intent": "booking"}}"""

    try:
        response = _get_llm().invoke(
            [SystemMessage(content=system), HumanMessage(content=last_user_msg)]
        )

        clean = response.content.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)

        if not isinstance(data, dict):
            data = {}

        print(f"🤖 [IA Extractor] Datos extraídos (LLM): {data}")

        return {
            "appointment_date": data.get("date"),
            "appointment_time": data.get("time"),
        }

    except Exception as e:
        print(f"❌ Error en extractor_node: {e}")
        return {
            "appointment_date": state.get("appointment_date"),
            "appointment_time": state.get("appointment_time"),
        }
