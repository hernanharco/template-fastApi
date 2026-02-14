# app/agents/config.py

# Palabras que activan el CATÁLOGO (Solo intención de curiosear)
# Quitamos "uñas", "manicura", etc. para que no atrapen la selección
SERVICE_KEYWORDS = [
    "servicio", "servicios", "qué ofrecen", "ofrecen",
    "precios", "cuánto cuesta", "catálogo", "lista", "opciones",
    "menú", "tarifas", "costos"
]

# Palabras que activan el AGENDAMIENTO (Intención de cita)
BOOKING_KEYWORDS = [
    "cita", "turno", "agendar", "reserva", "disponible",
    "quiero ir", "mañana", "lunes", "martes", "miercoles", "jueves", 
    "viernes", "sábado", "domingo", "pasado mañana", "hoy", "espacio",
    "hora", "horarios", "antes", "antes de", "después", "disponibilidad", "libre"
]

# Palabras que activan la CONFIRMACIÓN (Intención de confirmar)
CONFIRMATION_KEYWORDS = [
    "vale", "ok", "sí", "si", "perfecto", "de acuerdo", 
    "confirmo", "confirmado", "listo", "genial", "bien"
]