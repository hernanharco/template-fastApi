from enum import Enum


class Intent(str, Enum):
    """
    Intenciones principales del sistema.
    Usar Enum evita errores de strings en el flujo del agente.
    """

    GREETING = "GREETING"
    CATALOG = "CATALOG"
    BOOKING = "BOOKING"
    CONFIRMATION = "CONFIRMATION"
    FINISH = "FINISH"