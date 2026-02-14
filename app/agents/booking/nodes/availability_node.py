from datetime import datetime
from app.utils.availability import get_available_slots


def availability_node(state: dict, db) -> dict:
    date_str   = state.get("appointment_date")
    service_id = state.get("service_id")

    if not date_str or not service_id:
        return {"available_slots": None}

    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        slots = get_available_slots(db, target_date, service_id=service_id)

        if not slots:
            return {**state, "available_slots": "Sin disponibilidad"}

        def fmt(t):
            if hasattr(t, "strftime"):
                return t.strftime("%H:%M")
            return str(t)[:2]

        # ✅ Deduplicar por hora antes de mostrar
        seen, unique = set(), []
        for s in slots:
            label = fmt(s["start_time"])
            if label not in seen:
                seen.add(label)
                unique.append(s)

        formatted = ", ".join([fmt(s["start_time"]) for s in unique[:2]])
        return {**state, "available_slots": formatted}

    except Exception as e:
        print(f"❌ Error en availability_node: {e}")
        return {**state, "available_slots": "Error en agenda"}