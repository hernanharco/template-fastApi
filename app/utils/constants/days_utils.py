# app/utils/constants/days_utils.py (En tu FastAPI)
from datetime import datetime

_DAYS_MAP = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo"
}

def get_db_day_index(dt: datetime) -> int:
    """
    Convierte un objeto datetime al índice de tu DB (0=Lunes, 6=Domingo).
    Python's .weekday() ya devuelve 0 para Lunes.
    """
    return dt.weekday()

#la siguiente parte se utiliza en extractor_node.py de booking

DAYS_MAP = {
    "lunes": 0, "martes": 1, "miércoles": 2, "miercoles": 2,
    "jueves": 3, "viernes": 4, "sábado": 5, "sabado": 5, "domingo": 6,
}

def map_js_to_db_day(js_day: int) -> int:
    # Lógica que ya tenías para mapear si fuera necesario
    return 6 if js_day == 0 else js_day - 1