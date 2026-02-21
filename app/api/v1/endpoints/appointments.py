"""
API Router para la gestión de citas (appointments).
Este módulo contiene todos los endpoints CRUD, el sistema de disponibilidad
y la vinculación automática con el dominio de clientes.
"""

from datetime import date, datetime, time
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from pydantic import BaseModel

# Importaciones con rutas absolutas
from app.db.session import get_db
from app.models.appointments import Appointment, AppointmentStatus
from app.models.services import Service
from app.models.collaborators import Collaborator
from app.models.clients import Client
from app.schemas.appointments import (
    AppointmentCreate, AppointmentRead, AppointmentUpdate, 
    TimeSlot, AvailableSlotsResponse
)
from app.utils.availability import (
    get_available_slots, is_valid_appointment_time
)

router = APIRouter()

# --- 🟢 ENDPOINTS DE ESCRITURA ---

@router.post("/", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: AppointmentCreate, 
    db: Session = Depends(get_db)
):
    """
    Crea una nueva cita vinculando automáticamente al cliente por teléfono.
    """
    # 1. Validar Servicio
    service = db.query(Service).filter(
        and_(Service.id == appointment_data.service_id, Service.is_active == True)
    ).first()
    if not service:
        raise HTTPException(status_code=400, detail="Servicio no encontrado o inactivo")

    # 2. Asignación de Colaborador
    final_collaborator_id = appointment_data.collaborator_id
    if not final_collaborator_id:
        from app.utils.availability import find_available_collaborator
        final_collaborator_id = find_available_collaborator(
            db, appointment_data.start_time, appointment_data.end_time, appointment_data.service_id
        )
        if not final_collaborator_id:
            raise HTTPException(status_code=400, detail="No hay profesionales disponibles")
    
    # 3. Validar Conflictos
    is_valid, error = is_valid_appointment_time(db, final_collaborator_id, appointment_data.start_time, appointment_data.end_time)
    if not is_valid:
        raise HTTPException(status_code=409, detail=error)

    # 4. Gestión de Cliente (Buscar o Crear)
    client = None
    if appointment_data.client_phone:
        client = db.query(Client).filter(Client.phone == appointment_data.client_phone).first()

    if not client:
        client = Client(
            full_name=appointment_data.client_name,
            phone=appointment_data.client_phone,
            email=appointment_data.client_email
        )
        db.add(client)
        db.flush() 
    else:
        client.full_name = appointment_data.client_name
        if appointment_data.client_email:
            client.email = appointment_data.client_email

    # 5. Crear Cita
    appointment_dict = appointment_data.dict(exclude={'collaborator_id'})
    new_appointment = Appointment(
        **appointment_dict,
        collaborator_id=final_collaborator_id,
        client_id=client.id,
        status=AppointmentStatus.SCHEDULED
    )
    
    try:
        db.add(new_appointment)
        db.commit()
        db.refresh(new_appointment)
        return new_appointment
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# --- 🔵 ENDPOINTS DE LECTURA (FILTRADO) ---

@router.get("/", response_model=List[AppointmentRead])
async def get_appointments(
    date_filter: Optional[date] = Query(None, alias="date", description="Filtrar por día (YYYY-MM-DD)"),
    collaborator_id: Optional[int] = None,
    service_id: Optional[int] = None,
    status: Optional[AppointmentStatus] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Obtiene lista de citas. 
    Eliminamos el filtro is_active porque no existe en el modelo actual.
    """
    # 🎯 CAMBIO AQUÍ: Quitamos .filter(Appointment.is_active == True)
    query = db.query(Appointment)
    
    if date_filter:
        start_day = datetime.combine(date_filter, time.min)
        end_day = datetime.combine(date_filter, time.max)
        query = query.filter(Appointment.start_time.between(start_day, end_day))
    elif date_from or date_to:
        if date_from: query = query.filter(Appointment.start_time >= date_from)
        if date_to: query = query.filter(Appointment.start_time <= date_to)

    if collaborator_id:
        query = query.filter(Appointment.collaborator_id == collaborator_id)
    if service_id:
        query = query.filter(Appointment.service_id == service_id)
    if status:
        query = query.filter(Appointment.status == status)
    
    return query.order_by(Appointment.start_time.asc()).offset(skip).limit(limit).all()

@router.get("/{appointment_id}", response_model=AppointmentRead)
async def get_appointment(appointment_id: int, db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    return appointment

# --- 🟡 ENDPOINTS DE ACTUALIZACIÓN Y ELIMINACIÓN ---

@router.put("/{appointment_id}", response_model=AppointmentRead)
async def update_appointment(
    appointment_id: int,
    appointment_data: AppointmentUpdate,
    db: Session = Depends(get_db)
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    
    if appointment_data.start_time or appointment_data.collaborator_id:
        new_start = appointment_data.start_time or appointment.start_time
        new_end = appointment_data.end_time or appointment.end_time
        new_collab = appointment_data.collaborator_id or appointment.collaborator_id
        
        is_valid, error = is_valid_appointment_time(db, new_collab, new_start, new_end)
        if not is_valid:
            raise HTTPException(status_code=409, detail=error)
    
    update_data = appointment_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(appointment, field, value)
    
    db.commit()
    db.refresh(appointment)
    return appointment

@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: int,
    hard_delete: bool = False,
    db: Session = Depends(get_db)
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Cita no encontrada")
    
    if hard_delete:
        db.delete(appointment)
    else:
        # Borrado lógico: cambiamos estado a cancelado o is_active a False
        appointment.status = AppointmentStatus.CANCELLED
        appointment.is_active = False
    
    db.commit()

# --- 🟣 DISPONIBILIDAD Y ESTADÍSTICAS ---

@router.get("/availability/slots", response_model=AvailableSlotsResponse)
async def get_available_slots_endpoint(
    date: str,
    service_id: int,
    collaborator_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Use YYYY-MM-DD")
    
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    available_slots = get_available_slots(db, target_date, service_id, collaborator_id)
    
    slot_responses = [
        TimeSlot(
            start_time=s['start_time'],
            end_time=s['end_time'],
            collaborator_id=s['collaborator_id'],
            collaborator_name=s['collaborator_name'],
            available_minutes=s['available_minutes']
        ) for s in available_slots
    ]
    
    return AvailableSlotsResponse(
        date=date,
        service_id=service_id,
        service_duration=service.duration_minutes,
        available_slots=slot_responses,
        total_slots=len(slot_responses)
    )

@router.get("/stats/summary")
async def get_appointments_summary(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Appointment)
    if date_from: query = query.filter(Appointment.start_time >= date_from)
    if date_to: query = query.filter(Appointment.start_time <= date_to)
    
    total = query.count()
    completed = query.filter(Appointment.status == AppointmentStatus.COMPLETED).count()
    
    return {
        "total_appointments": total,
        "scheduled": query.filter(Appointment.status == AppointmentStatus.SCHEDULED).count(),
        "confirmed": query.filter(Appointment.status == AppointmentStatus.CONFIRMED).count(),
        "completed": completed,
        "cancelled": query.filter(Appointment.status == AppointmentStatus.CANCELLED).count(),
        "completion_rate": round((completed / total * 100) if total > 0 else 0, 2)
    }

# 1. Definición primero
class WeeklyCountResponse(BaseModel):
    counts: Dict[str, int]

@router.post("/summary", response_model=WeeklyCountResponse)
async def get_appointments_summary(
    dates: List[str] = Body(...), 
    db: Session = Depends(get_db)
):
    """
    🎯 Endpoint para el carrusel de Svelte.
    Recibe una lista de fechas ["2026-02-20", "2026-02-21"]
    y devuelve el conteo de citas de cada una.
    """
    
    # 1. Convertimos los strings a fechas reales para filtrar en SQL
    # Esto es vital para el aislamiento físico y seguridad en Neon [cite: 2026-02-18]
    parsed_dates = []
    for d in dates:
        try:
            parsed_dates.append(datetime.strptime(d, "%Y-%m-%d").date())
        except ValueError:
            continue # Ignoramos fechas mal formateadas

    # 2. Consulta agrupada (GROUP BY)
    # Pedimos a PostgreSQL que cuente por día
    results = (
        db.query(
            func.date(Appointment.start_time).label("day"),
            func.count(Appointment.id).label("total")
        )
        .filter(func.date(Appointment.start_time).in_(parsed_dates))
        .group_by(func.date(Appointment.start_time))
        .all()
    )

    # 3. Mapeamos los resultados a un diccionario
    # Convertimos el objeto date de nuevo a string para el JSON
    counts_map = {res.day.strftime("%Y-%m-%d"): res.total for res in results}

    # 4. Aseguramos que todas las fechas solicitadas tengan un valor (aunque sea 0)
    final_counts = {date: counts_map.get(date, 0) for date in dates}

    return {"counts": final_counts}