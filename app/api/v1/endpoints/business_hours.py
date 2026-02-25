"""
Router para la gestión de horarios de negocio (Business Hours).
Implementa operaciones masivas (Bulk) para optimizar la comunicación con Neon/PostgreSQL.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import time

# Importaciones del núcleo
from app.db.session import get_db
from app.models.collaborators import Collaborator
from app.models.business_hours import BusinessHours, TimeSlot

# 🎯 Importaciones de esquemas actualizadas (Solo lo que existe)
from app.schemas.business_hours import (
    BusinessHoursRead,
    BulkBusinessHoursUpdate
)

router = APIRouter()

@router.get("/global-range")
async def get_global_opening_range(
    day_of_week: int = Query(..., ge=0, le=6),
    db: Session = Depends(get_db)
):
    """
    Calcula los intervalos reales de apertura del local basándose 
    en colaboradores activos (Merging Intervals Algorithm).
    """
    slots = db.query(TimeSlot).join(BusinessHours).join(Collaborator).filter(
        and_(
            BusinessHours.day_of_week == day_of_week,
            BusinessHours.is_enabled == True,
            Collaborator.is_active == True
        )
    ).order_by(TimeSlot.start_time).all()

    if not slots:
        return {"ranges": [], "is_open": False}

    merged_ranges = []
    current_start = slots[0].start_time
    current_end = slots[0].end_time

    for next_slot in slots[1:]:
        if next_slot.start_time <= current_end:
            # Solapamiento detectado: extendemos el final si es necesario
            current_end = max(current_end, next_slot.end_time)
        else:
            # Hueco detectado: cerramos el rango actual y empezamos uno nuevo
            merged_ranges.append({
                "start": current_start.strftime("%H:%M"),
                "end": current_end.strftime("%H:%M")
            })
            current_start = next_slot.start_time
            current_end = next_slot.end_time
    
    # Añadimos el último segmento procesado
    merged_ranges.append({
        "start": current_start.strftime("%H:%M"),
        "end": current_end.strftime("%H:%M")
    })

    return {
        "ranges": merged_ranges,
        "is_open": True,
        "min_start": merged_ranges[0]["start"],
        "max_end": merged_ranges[-1]["end"]
    }

@router.get("/", response_model=List[BusinessHoursRead])
async def get_business_hours(
    collaborator_id: int = Query(..., description="ID del colaborador obligatorio"),
    db: Session = Depends(get_db)
):
    """Obtiene la configuración semanal completa del colaborador."""
    business_hours = db.query(BusinessHours).filter(
        BusinessHours.collaborator_id == collaborator_id
    ).order_by(BusinessHours.day_of_week).all()
    
    # 💡 Ordenar slots cronológicamente antes de enviar al frontend
    for bh in business_hours:
        bh.time_slots.sort(key=lambda x: x.start_time)
        
    return business_hours

@router.post("/bulk-update", status_code=status.HTTP_200_OK)
async def bulk_update_business_hours(
    payload: BulkBusinessHoursUpdate,
    db: Session = Depends(get_db)
):
    """
    🚀 ENDPOINT CORE: Actualización Atómica de la semana.
    Aplica el patrón: Eliminar existentes -> Insertar nuevos.
    """
    try:
        # 1. Limpieza de horarios previos del colaborador
        # synchronize_session=False es más rápido para borrados masivos
        db.query(BusinessHours).filter(
            BusinessHours.collaborator_id == payload.collaborator_id
        ).delete(synchronize_session=False)

        # 2. Inserción de la nueva configuración recibida
        for day_data in payload.schedules:
            # Solo guardamos los días habilitados para mantener la DB limpia
            if not day_data.is_enabled:
                continue

            new_bh = BusinessHours(
                day_of_week=day_data.day_of_week,
                day_name=day_data.day_name,
                is_enabled=day_data.is_enabled,
                is_split_shift=day_data.is_split_shift,
                collaborator_id=payload.collaborator_id
            )
            db.add(new_bh)
            db.flush() # Flush para obtener el ID de new_bh sin hacer commit aún

            # Inserción de los slots de tiempo del día
            for slot_data in day_data.time_slots:
                new_slot = TimeSlot(
                    start_time=slot_data.start_time,
                    end_time=slot_data.end_time,
                    slot_order=slot_data.slot_order,
                    business_hours_id=new_bh.id
                )
                db.add(new_slot)

        # 3. Commit de toda la transacción si todo salió bien
        db.commit()
        return {"status": "success", "message": "Calendario actualizado correctamente"}

    except Exception as e:
        # ⚠️ Ante cualquier error, revertimos todo para evitar estados inconsistentes
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar el guardado masivo: {str(e)}"
        )

@router.delete("/{business_hours_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_business_hours(business_hours_id: int, db: Session = Depends(get_db)):
    """Elimina un día específico por ID."""
    db_bh = db.query(BusinessHours).filter(BusinessHours.id == business_hours_id).first()
    if not db_bh:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(db_bh)
    db.commit()
    return None