"""
Router principal de la API v1.
Este módulo agrupa todos los endpoints de la versión 1 de la API.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import services, business_hours, collaborators, appointments, availability, ai_booking, clients

# 1. Creamos el router sin prefijo de versión.
# El prefijo /api/v1 ya lo pone el main.py
api_router = APIRouter()

# 2. Incluimos los routers de cada dominio.
# Aquí definimos el nombre del recurso (services, business-hours, collaborators, appointments, etc.)

# Dominio de Servicios
api_router.include_router(
    services.router,
    prefix="/services",
    tags=["services"]
)

# Dominio de Horarios
api_router.include_router(
    business_hours.router,
    prefix="/business-hours", 
    tags=["business-hours"]
)

# Dominio de Colaboradores
api_router.include_router(
    collaborators.router,
    prefix="/collaborators",
    tags=["collaborators"]
)

# Dominio de Citas
api_router.include_router(
    appointments.router,
    prefix="/appointments",
    tags=["appointments"]
)

# Dominio de Disponibilidad
api_router.include_router(
    availability.router,
    prefix="/availability",
    tags=["availability"]
)

# Dominio de ai-booking
api_router.include_router(
    ai_booking.router,
    prefix="/ai_booking",
    tags=["ai_booking"]
)

# Dominio de Clientes
api_router.include_router(
    clients.router,
    prefix="/clients",
    tags=["clients"]
)
