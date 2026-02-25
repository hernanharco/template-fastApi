"""
API Router para la gestión de citas (appointments).
Mantiene exclusivamente las operaciones CRUD y consultas de estado.
"""

from datetime import date, datetime, time
from typing import List, Optional, Dict # 👈 Recuperado Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, func

# --- IMPORTACIONES DE MODELOS ---
from app.models.appointments import Appointment, AppointmentStatus
from app.models.services import Service  # 🎯 Necesario para el joinedload
# -------------------------------

from app.api.v1.endpoints.notifications import notify_appointment_change
from app.db.session import get_db
from app.schemas.appointments import (
    AppointmentCreate,
    AppointmentRead,
    AppointmentUpdate,
    DayCountResponse,
)
from app.services.availability import is_valid_appointment_time
from app.services import appointment_service # 👈 Recuperado

# El Manager centraliza la lógica compleja (crear cliente + cita)
from app.services.appointment_manager import appointment_manager

router = APIRouter()


# --- 🟢 CREACIÓN (CREATE) ---
@router.post("/", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: AppointmentCreate, db: Session = Depends(get_db)
):
    """
    Registra una cita.
    Llama al 'appointment_manager' para que él se encargue de buscar/crear el cliente
    y validar si el profesional está disponible.
    """
    try:
        appointment = await appointment_manager.create_full_appointment(db, appointment_data)
        
        # 📢 AVISO EN TIEMPO REAL: Se creó una cita (Manual o vía IA)
        await notify_appointment_change()
        
        return appointment
    except ValueError as e:
        # Errores de validación (ej: "Profesional ocupado")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        # Errores inesperados del servidor
        raise HTTPException(status_code=500, detail="Error interno al crear la cita")


# --- 🔵 LECTURA Y FILTRADO (READ) ---


@router.get("/", response_model=List[AppointmentRead])
async def get_appointments(
    date_filter: Optional[date] = Query(
        None, alias="date", description="Filtrar por día YYYY-MM-DD"
    ),
    collaborator_id: Optional[int] = None,
    status: Optional[AppointmentStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db),
):
    """
    Lista las citas permitiendo filtrar por fecha, profesional o estado.
    Incluye Eager Loading para traer colores de departamentos.
    """
    # 🎯 Aplicamos joinedload para que el frontend reciba el color del departamento
    query = db.query(Appointment).options(
        joinedload(Appointment.service).joinedload(Service.department)
    )

    # Si pasan una fecha, filtramos desde las 00:00 hasta las 23:59 de ese día
    if date_filter:
        start_day = datetime.combine(date_filter, time.min)
        end_day = datetime.combine(date_filter, time.max)
        query = query.filter(Appointment.start_time.between(start_day, end_day))

    if collaborator_id:
        query = query.filter(Appointment.collaborator_id == collaborator_id)
    if status:
        query = query.filter(Appointment.status == status)

    return query.order_by(Appointment.start_time.asc()).offset(skip).limit(limit).all()


@router.get("/count-by-day", response_model=DayCountResponse)
async def get_single_day_count(
    target_date: date = Query(..., description="Fecha para consultar (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """
    Obtiene el número de citas para un día específico.
    """
    # Filtramos el rango completo del día
    start_day = datetime.combine(target_date, time.min)
    end_day = datetime.combine(target_date, time.max)

    count = (
        db.query(Appointment)
        .filter(
            and_(
                Appointment.start_time >= start_day,
                Appointment.start_time <= end_day,
                # Solo contamos citas reales (no canceladas)
                Appointment.status != AppointmentStatus.CANCELLED,
            )
        )
        .count()
    )

    # Retornamos el objeto siguiendo el esquema DayCountResponse
    return DayCountResponse(date=target_date, count=count)

@router.get("/counts-range", response_model=Dict[str, int])
async def get_appointments_counts_range(
    start: str = Query(..., description="Fecha inicio YYYY-MM-DD"), # 👈 Cambiado a str
    end: str = Query(..., description="Fecha fin YYYY-MM-DD"),     # 👈 Cambiado a str
    db: Session = Depends(get_db),
):
    """
    🚀 OPTIMIZACIÓN: Obtiene el conteo de citas para un rango de fechas.
    Ideal para refrescar todo el carrusel del Dashboard en una sola petición.
    """
    try:
        # Convertimos manualmente los strings a objetos date
        d_start = date.fromisoformat(start)
        d_end = date.fromisoformat(end)

        start_dt = datetime.combine(d_start, time.min)
        end_dt = datetime.combine(d_end, time.max)

        results = (
            db.query(
                func.date(Appointment.start_time).label("day"),
                func.count(Appointment.id).label("count")
            )
            .filter(
                and_(
                    Appointment.start_time >= start_dt,
                    Appointment.start_time <= end_dt,
                    Appointment.status != AppointmentStatus.CANCELLED
                )
            )
            .group_by(func.date(Appointment.start_time))
            .all()
        )

        # 🎯 IMPORTANTE: Forzamos que la llave sea string para evitar líos de serialización
        return {str(row.day): row.count for row in results}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Use YYYY-MM-DD")

# @router.get("/{appointment_id}", response_model=AppointmentRead)
# async def get_appointment(appointment_id: int, db: Session = Depends(get_db)):
#     """Obtiene el detalle de una sola cita por su ID incluyendo relaciones."""
#     appointment = (
#         db.query(Appointment)
#         .options(joinedload(Appointment.service).joinedload(Service.department))
#         .filter(Appointment.id == appointment_id)
#         .first()
#     )
#     if not appointment:
#         raise HTTPException(status_code=404, detail="Cita no encontrada")
#     return appointment


# --- 🟡 ACTUALIZACIÓN (UPDATE) ---
@router.put("/{appointment_id}", response_model=AppointmentRead)
async def update_appointment(
    appointment_id: int,
    appointment_data: AppointmentUpdate,
    db: Session = Depends(get_db),
):
    """
    Modifica una cita. Si se cambia la fecha o el profesional,
    vuelve a validar la disponibilidad.
    """
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Cita no encontrada")

    # Si el usuario intenta cambiar fecha o profesional, validamos que el nuevo hueco esté libre
    if appointment_data.start_time or appointment_data.collaborator_id:
        new_start = appointment_data.start_time or appointment.start_time
        new_end = appointment_data.end_time or appointment.end_time
        new_collab = appointment_data.collaborator_id or appointment.collaborator_id

        is_valid, error = is_valid_appointment_time(db, new_collab, new_start, new_end)
        if not is_valid:
            raise HTTPException(status_code=409, detail=error)

    # Aplicamos los cambios campo por campo
    update_data = appointment_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(appointment, field, value)

    db.commit()
    db.refresh(appointment)

    # 📢 AVISO EN TIEMPO REAL: Se modificó una cita existente
    await notify_appointment_change()

    return appointment


# --- 🔴 ELIMINACIÓN (DELETE) ---
@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(appointment_id: int, db: Session = Depends(get_db)):
    """
    Cancela una cita.
    En lugar de borrarla físicamente, le cambiamos el estado a 'CANCELLED'.
    """
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Cita no encontrada")

    appointment.status = AppointmentStatus.CANCELLED
    db.commit()

    # 📢 AVISO EN TIEMPO REAL: Se canceló una cita, el hueco queda libre
    await notify_appointment_change()

    return None