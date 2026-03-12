from app.agents.nodes.time_filter_node import TimeFilterResult


def extract_hour_range(filter_result: TimeFilterResult) -> tuple[int | None, int | None]:
    """Devuelve (min_hour, max_hour) según el modo del filtro."""
    mode = filter_result.mode
    if mode == "after":
        return filter_result.after_hour, None
    if mode == "before":
        return None, filter_result.before_hour
    if mode == "between":
        return filter_result.after_hour, filter_result.before_hour
    return None, None


def filter_description(filter_result: TimeFilterResult) -> str:
    """Texto legible del filtro para incluir en mensajes al usuario."""
    mode = filter_result.mode
    if mode == "after" and filter_result.after_hour is not None:
        return f"después de las {_hour_label(filter_result.after_hour)}"
    if mode == "before" and filter_result.before_hour is not None:
        return f"antes de las {_hour_label(filter_result.before_hour)}"
    if mode == "between" and filter_result.after_hour and filter_result.before_hour:
        return f"entre las {_hour_label(filter_result.after_hour)} y las {_hour_label(filter_result.before_hour)}"
    if mode == "first":
        return "a primera hora"
    if mode == "last":
        return "a última hora"
    return "con esa preferencia"


def _hour_label(hour: int) -> str:
    suffix = "AM" if hour < 12 else "PM"
    display = hour if hour <= 12 else hour - 12
    if display == 0:
        display = 12
    return f"{display}:00 {suffix}"