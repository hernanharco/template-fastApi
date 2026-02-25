"""
API Router para la consulta de disponibilidad.
Este endpoint actúa como interfaz entre el Frontend (Astro) y nuestro motor de disponibilidad.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional

from app.db.session import get_db
# 🚀 Cambiado a app.services para seguir la arquitectura de dominios
from app.services.availability import get_available_slots 
from app.schemas.appointments import AvailableSlotsResponse
from app.models.services import Service

router = APIRouter() 

@router.get("/", response_model=AvailableSlotsResponse)
def read_availability(
    *,
    db: Session = Depends(get_db),
    date: str = Query(..., description="Fecha en formato YYYY-MM-DD", examples=["2026-02-25"]),
    service_id: int = Query(..., description="ID del servicio que se desea reservar"),
    collaborator_id: Optional[int] = Query(None, description="ID opcional de un profesional específico")
):
    """
    Endpoint para obtener los slots disponibles.
    Calcula en tiempo real los huecos libres basado en el departamento del servicio.
    """
    # 1. Validación de entrada (Date Parsing)
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Formato de fecha inválido. Use YYYY-MM-DD"
        )
    
    # 2. Verificación de negocio previa
    service = db.query(Service).filter(
        Service.id == service_id, 
        Service.is_active == True
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=404, 
            detail="El servicio solicitado no existe o no está activo"
        )
    
    # 3. Ejecución de la lógica de dominio (Core de la App)
    try:
        slots = get_available_slots(
            db=db,
            target_date=target_date,
            service_id=service_id,
            collaborator_id=collaborator_id
        )
        
        # 4. Construcción de respuesta (Validada por AvailableSlotsResponse)
        return {
            "date": date,
            "service_id": service_id,
            "service_duration": service.duration_minutes,
            "available_slots": slots,
            "total_slots": len(slots)
        }

    except Exception as e:
        # Aquí podrías usar un logger real como Loguru o Sentry en el futuro
        print(f"❌ Error en motor de disponibilidad: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Error interno al calcular huecos disponibles"
        )