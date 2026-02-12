"""
API Router para la consulta de disponibilidad.
Este endpoint calcula los huecos libres (slots) basándose en:
1. Horarios laborales (BusinessHours) de los colaboradores.
2. Citas existentes (Appointments) para evitar solapamientos.
3. Duración del servicio solicitado.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional

from app.db.session import get_db
from app.models.services import Service
from app.utils.availability import get_available_slots 
from app.schemas.appointments import AvailableSlotsResponse # 👈 Importante para el formato

router = APIRouter() 

@router.get("/", response_model=AvailableSlotsResponse)
def read_availability(
    *,
    db: Session = Depends(get_db),
    date: str = Query(..., description="Fecha en formato YYYY-MM-DD", example="2026-02-14"),
    service_id: int = Query(..., description="ID del servicio que se desea reservar"),
    collaborator_id: Optional[int] = Query(None, description="ID opcional de un profesional específico")
):
    """
    Endpoint para obtener los slots disponibles.
    Devuelve una lista de horarios de inicio y fin donde el servicio puede ser realizado.
    """
    try:
        # 1. Validar formato de fecha y convertir a objeto datetime Naive
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail="Formato de fecha inválido. Use YYYY-MM-DD"
            )
        
        # 2. Verificar que el servicio exista para obtener su duración
        service = db.query(Service).filter(
            Service.id == service_id, 
            Service.is_active == True
        ).first()
        
        if not service:
            raise HTTPException(
                status_code=404, 
                detail="El servicio solicitado no existe o no está activo"
            )
        
        # 3. Llamar a la lógica de cálculo en utils/availability.py
        # Esta función ya maneja la lógica de filtrar citas y horarios laborales
        slots = get_available_slots(
            db=db,
            target_date=target_date,
            service_id=service_id,
            collaborator_id=collaborator_id
        )
        
        # 4. Construir la respuesta que espera el Schema AvailableSlotsResponse
        # Al pasar por el Schema, las fechas se limpian de la "T" y zonas horarias
        return {
            "date": date,
            "service_id": service_id,
            "service_duration": service.duration_minutes,
            "available_slots": slots,
            "total_slots": len(slots)
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        # Log del error para debugging
        print(f"❌ Error crítico en disponibilidad: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Error interno al calcular la disponibilidad"
        )

# --- NOTA PARA EL DESARROLLADOR JUNIOR ---
# 1. El 'response_model' es quien hace la "magia" de convertir los objetos 
#    datetime de Python al formato string que definimos en el Schema.
# 2. Si devuelves solo 'slots' (como una lista), FastAPI se salta la validación
#    del Schema 'AvailableSlotsResponse' y por eso veías las horas mal.