"""
ExtractorNode — Dominio: Appointments
Responsabilidad única: extraer la hora elegida por el usuario.
No interpreta fechas — eso ya lo hizo booking.
"""

import re


def extractor_node(state: dict) -> dict:
    # ✅ Buscar el último mensaje del usuario, no el último en general
    # (el último puede ser del asistente si ya respondió en este turno)
    messages = state.get("messages", [])
    user_msgs = [m for m in messages if m.get("role") == "user"]
    last_msg  = user_msgs[-1]["content"].strip() if user_msgs else ""

    time_str = _parse_time(last_msg)

    print(f"🕐 [Appointments Extractor] Hora detectada: {time_str} (msg: '{last_msg}')")

    # ✅ {**state} para no perder el state en el grafo
    return {**state, "appointment_time": time_str}


def _parse_time(msg: str) -> str | None:
    """
    Extrae una hora de cualquier mensaje, aunque tenga texto extra.
    Acepta: "13:00", "13.00", "13.00 esta bien", "a las 1", "las 13",
            "9:30 por fa", "10h30", "a las 13:00 por favor"
    Devuelve "HH:MM" o None.
    """
    clean = msg.lower().strip()

    # Eliminar palabras clave de cortesía que interfieren
    clean = re.sub(r"\b(a\s*las?|por\s*fa(?:vor)?|porfa|ok|vale|bien|esta|quiero|prefiero)\b", "", clean)
    # Normalizar separadores h y punto → ":"
    clean = re.sub(r"(\d)\s*h\s*(\d)", r"\1:\2", clean)   # 9h30 → 9:30
    clean = re.sub(r"(\d)\.(\d)", r"\1:\2", clean)          # 13.00 → 13:00

    # Buscar patrón HH:MM o solo HH dentro del texto (search, no fullmatch)
    match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\b", clean)
    if match:
        h = int(match.group(1))
        m = int(match.group(2)) if match.group(2) else 0
        if 0 <= h <= 23 and 0 <= m <= 59:
            return f"{h:02d}:{m:02d}"

    return None