# app/api/v1/endpoints/business_hours.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import time, datetime

from app.models.collaborators import Collaborator

from app.db.session import get_db
from app.models.business_hours import BusinessHours, TimeSlot
from app.schemas.business_hours import (
    BusinessHoursCreate, BusinessHoursRead, BusinessHoursUpdate
)

router = APIRouter()

@router.get("/global-range")
async def get_global_opening_range(
    day_of_week: int = Query(..., ge=0, le=6),
    db: Session = Depends(get_db)
):
    """
    Calcula los intervalos reales de apertura del local basándose 
    en colaboradores activos.
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

    # Lógica para combinar rangos que se solapan (Merging intervals)
    # Si el Colab A cierra a las 14:00 y el Colab B abre a las 13:30, 
    # el local sigue abierto de corrido.
    merged_ranges = []
    if slots:
        current_start = slots[0].start_time
        current_end = slots[0].end_time

        for next_slot in slots[1:]:
            if next_slot.start_time <= current_end:
                # Si el siguiente empieza antes de que el actual termine, extendemos
                current_end = max(current_end, next_slot.end_time)
            else:
                # Hay un hueco, guardamos el rango anterior y empezamos uno nuevo
                merged_ranges.append({
                    "start": current_start.strftime("%H:%M"),
                    "end": current_end.strftime("%H:%M")
                })
                current_start = next_slot.start_time
                current_end = next_slot.end_time
        
        # Añadimos el último rango
        merged_ranges.append({
            "start": current_start.strftime("%H:%M"),
            "end": current_end.strftime("%H:%M")
        })

    return {
        "ranges": merged_ranges,
        "is_open": len(merged_ranges) > 0,
        # Mantenemos start/end global para el tamaño de la tabla
        "min_start": merged_ranges[0]["start"],
        "max_end": merged_ranges[-1]["end"]
    }

@router.get("/", response_model=List[BusinessHoursRead])
async def get_business_hours(
    collaborator_id: int = Query(..., description="ID del colaborador obligatorio"),
    enabled_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Obtiene los horarios con sus slots ordenados cronológicamente."""
    query = db.query(BusinessHours).filter(BusinessHours.collaborator_id == collaborator_id)
    
    if enabled_only:
        query = query.filter(BusinessHours.is_enabled == True)
    
    business_hours = query.order_by(BusinessHours.day_of_week).all()
    
    # 💡 MEJORA CRÍTICA: Aseguramos que los slots dentro de cada día 
    # estén ordenados por hora de inicio antes de enviarlos al frontend.
    for bh in business_hours:
        bh.time_slots.sort(key=lambda x: x.start_time)
        
    return business_hours

@router.post("/", response_model=BusinessHoursRead, status_code=status.HTTP_201_CREATED)
async def create_business_hours(
    business_hours_data: BusinessHoursCreate,
    db: Session = Depends(get_db)
):
    existing_hours = db.query(BusinessHours).filter(
        and_(
            BusinessHours.day_of_week == business_hours_data.day_of_week,
            BusinessHours.collaborator_id == business_hours_data.collaborator_id
        )
    ).first()
    
    if existing_hours:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe configuración para este colaborador el día {business_hours_data.day_name}"
        )
    
    new_bh = BusinessHours(
        day_of_week=business_hours_data.day_of_week,
        day_name=business_hours_data.day_name,
        is_enabled=business_hours_data.is_enabled,
        is_split_shift=business_hours_data.is_split_shift,
        collaborator_id=business_hours_data.collaborator_id
    )
    db.add(new_bh)
    db.flush() 
    
    for slot_data in business_hours_data.time_slots:
        start = slot_data.start_time if isinstance(slot_data.start_time, time) else datetime.strptime(slot_data.start_time, "%H:%M").time()
        end = slot_data.end_time if isinstance(slot_data.end_time, time) else datetime.strptime(slot_data.end_time, "%H:%M").time()
        
        db.add(TimeSlot(
            start_time=start,
            end_time=end,
            slot_order=slot_data.slot_order,
            business_hours_id=new_bh.id
        ))
    
    db.commit()
    db.refresh(new_bh)
    return new_bh

@router.put("/{business_hours_id}", response_model=BusinessHoursRead)
async def update_business_hours(
    business_hours_id: int,
    update_data: BusinessHoursUpdate,
    db: Session = Depends(get_db)
):
    db_bh = db.query(BusinessHours).filter(BusinessHours.id == business_hours_id).first()
    if not db_bh:
        raise HTTPException(status_code=404, detail="No encontrado")

    # Actualizamos campos básicos
    for key, value in update_data.model_dump(exclude={'time_slots'}, exclude_unset=True).items():
        setattr(db_bh, key, value)

    # Reemplazo de slots (Naive Time)
    if update_data.time_slots is not None:
        db.query(TimeSlot).filter(TimeSlot.business_hours_id == business_hours_id).delete()
        for slot_data in update_data.time_slots:
            start = slot_data.start_time if isinstance(slot_data.start_time, time) else datetime.strptime(slot_data.start_time, "%H:%M").time()
            end = slot_data.end_time if isinstance(slot_data.end_time, time) else datetime.strptime(slot_data.end_time, "%H:%M").time()
            db.add(TimeSlot(start_time=start, end_time=end, slot_order=slot_data.slot_order, business_hours_id=db_bh.id))

    db.commit()
    db.refresh(db_bh)
    db_bh.time_slots.sort(key=lambda x: x.start_time) # Ordenar antes de responder
    return db_bh

@router.delete("/{business_hours_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_business_hours(business_hours_id: int, db: Session = Depends(get_db)):
    db_bh = db.query(BusinessHours).filter(BusinessHours.id == business_hours_id).first()
    if not db_bh:
        raise HTTPException(status_code=404, detail="No encontrado")
    db.delete(db_bh)
    db.commit()
    return None