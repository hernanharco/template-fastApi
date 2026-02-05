"""
API Router para la gestión de citas (appointments).
Este módulo contiene todos los endpoints CRUD y el sistema de disponibilidad.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

# Importaciones con rutas absolutas
from app.db.session import get_db
from app.models.appointments import Appointment, AppointmentStatus
from app.models.services import Service
from app.models.collaborators import Collaborator
from app.schemas.appointments import (
    AppointmentCreate, AppointmentRead, AppointmentUpdate, 
    TimeSlot, AvailableSlotsResponse
)
from app.utils.availability import (
    get_available_slots, is_valid_appointment_time, 
    check_appointment_conflict
)

# Creamos el router de FastAPI para este dominio
router = APIRouter()


@router.post("/", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: AppointmentCreate, 
    db: Session = Depends(get_db)
):
    """
    Crea una nueva cita en el sistema.
    
    Este endpoint implementa la lógica anti-conflictos:
    1. Valida que el servicio y colaborador existan
    2. Verifica que no haya conflictos de horario
    3. Confirma que el horario esté dentro del business hours
    4. Crea la cita solo si todo es válido
    
    Args:
        appointment_data: Datos de la cita a crear
        db: Sesión de base de datos
    
    Returns:
        AppointmentRead: La cita creada con su ID
    
    Raises:
        HTTPException: Si hay conflictos o datos inválidos
    """
    
    # 1. Validar que el servicio exista y esté activo
    service = db.query(Service).filter(
        and_(Service.id == appointment_data.service_id, Service.is_active == True)
    ).first()
    
    if not service:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Servicio con ID {appointment_data.service_id} no encontrado o no está activo"
        )
    
    # 2. Validar que el colaborador exista y esté activo
    collaborator = db.query(Collaborator).filter(
        and_(Collaborator.id == appointment_data.collaborator_id, Collaborator.is_active == True)
    ).first()
    
    if not collaborator:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Colaborador con ID {appointment_data.collaborator_id} no encontrado o no está activo"
        )
    
    # 3. Validar el horario (business hours + conflictos)
    is_valid, error_message = is_valid_appointment_time(
        db, 
        appointment_data.collaborator_id,
        appointment_data.start_time,
        appointment_data.end_time
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_message
        )
    
    # 4. Crear la nueva cita
    new_appointment = Appointment(
        service_id=appointment_data.service_id,
        collaborator_id=appointment_data.collaborator_id,
        client_name=appointment_data.client_name,
        client_phone=appointment_data.client_phone,
        client_email=appointment_data.client_email,
        client_notes=appointment_data.client_notes,
        start_time=appointment_data.start_time,
        end_time=appointment_data.end_time,
        status=AppointmentStatus.SCHEDULED
    )
    
    # Guardar en la base de datos
    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)
    
    return new_appointment


@router.get("/", response_model=List[AppointmentRead])
async def get_appointments(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros a devolver"),
    collaborator_id: Optional[int] = Query(None, description="Filtrar por colaborador"),
    service_id: Optional[int] = Query(None, description="Filtrar por servicio"),
    status: Optional[AppointmentStatus] = Query(None, description="Filtrar por estado"),
    date_from: Optional[datetime] = Query(None, description="Fecha de inicio del rango"),
    date_to: Optional[datetime] = Query(None, description="Fecha de fin del rango"),
    db: Session = Depends(get_db)
):
    """
    Obtiene la lista de citas con filtros opcionales.
    
    Args:
        skip: Número de registros a omitir (paginación)
        limit: Número máximo de registros a devolver
        collaborator_id: Filtrar por colaborador específico
        service_id: Filtrar por servicio específico
        status: Filtrar por estado
        date_from: Fecha de inicio del rango
        date_to: Fecha de fin del rango
        db: Sesión de base de datos
    
    Returns:
        List[AppointmentRead]: Lista de citas encontradas
    """
    
    query = db.query(Appointment)
    
    # Aplicar filtros
    if collaborator_id:
        query = query.filter(Appointment.collaborator_id == collaborator_id)
    
    if service_id:
        query = query.filter(Appointment.service_id == service_id)
    
    if status:
        query = query.filter(Appointment.status == status)
    
    if date_from:
        query = query.filter(Appointment.start_time >= date_from)
    
    if date_to:
        query = query.filter(Appointment.start_time <= date_to)
    
    # Aplicar paginación y ordenamiento
    appointments = query.order_by(Appointment.start_time.desc()).offset(skip).limit(limit).all()
    
    return appointments


@router.get("/{appointment_id}", response_model=AppointmentRead)
async def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene una cita específica por su ID.
    
    Args:
        appointment_id: ID de la cita a buscar
        db: Sesión de base de datos
    
    Returns:
        AppointmentRead: La cita encontrada
    
    Raises:
        HTTPException: Si la cita no existe
    """
    
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cita con ID {appointment_id} no encontrada"
        )
    
    return appointment


@router.put("/{appointment_id}", response_model=AppointmentRead)
async def update_appointment(
    appointment_id: int,
    appointment_data: AppointmentUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza una cita existente.
    
    Este endpoint también previene conflictos al actualizar horarios.
    
    Args:
        appointment_id: ID de la cita a actualizar
        appointment_data: Datos a actualizar
        db: Sesión de base de datos
    
    Returns:
        AppointmentRead: La cita actualizada
    
    Raises:
        HTTPException: Si la cita no existe o hay conflictos
    """
    
    # Buscar la cita existente
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cita con ID {appointment_id} no encontrada"
        )
    
    # Si se está actualizando el horario, validar conflictos
    if appointment_data.start_time or appointment_data.end_time or appointment_data.collaborator_id:
        new_start = appointment_data.start_time or appointment.start_time
        new_end = appointment_data.end_time or appointment.end_time
        new_collaborator_id = appointment_data.collaborator_id or appointment.collaborator_id
        
        # Validar el nuevo horario
        is_valid, error_message = is_valid_appointment_time(
            db, new_collaborator_id, new_start, new_end
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_message
            )
    
    # Actualizar solo los campos proporcionados
    update_data = appointment_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(appointment, field, value)
    
    # Guardar cambios
    db.commit()
    db.refresh(appointment)
    
    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: int,
    hard_delete: bool = Query(False, description="Si es True, elimina permanentemente el registro"),
    db: Session = Depends(get_db)
):
    """
    Elimina una cita (soft delete por defecto).
    
    Args:
        appointment_id: ID de la cita a eliminar
        hard_delete: Si es True, elimina permanentemente
        db: Sesión de base de datos
    
    Raises:
        HTTPException: Si la cita no existe
    """
    
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cita con ID {appointment_id} no encontrada"
        )
    
    if hard_delete:
        # Eliminación permanente
        db.delete(appointment)
    else:
        # Soft delete: marcar como cancelada
        appointment.status = AppointmentStatus.CANCELLED
    
    db.commit()


@router.get("/availability/slots", response_model=AvailableSlotsResponse)
async def get_available_slots_endpoint(
    date: str = Query(..., description="Fecha en formato YYYY-MM-DD"),
    service_id: int = Query(..., gt=0, description="ID del servicio"),
    collaborator_id: Optional[int] = Query(None, description="ID del colaborador (opcional)"),
    db: Session = Depends(get_db)
):
    """
    Obtiene los huecos libres disponibles para un servicio en una fecha específica.
    
    Este endpoint utiliza la lógica anti-conflictos para mostrar solo horarios
    realmente disponibles sin solapamientos.
    
    Args:
        date: Fecha a consultar (YYYY-MM-DD)
        service_id: ID del servicio
        collaborator_id: ID del colaborador (opcional)
        db: Sesión de base de datos
    
    Returns:
        AvailableSlotsResponse: Huecos disponibles
    
    Raises:
        HTTPException: Si la fecha es inválida o el servicio no existe
    """
    
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato de fecha inválido. Use YYYY-MM-DD"
        )
    
    # Validar que el servicio exista
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Servicio con ID {service_id} no encontrado"
        )
    
    # Obtener huecos disponibles
    available_slots = get_available_slots(db, target_date, service_id, collaborator_id)
    
    # Convertir al formato de respuesta
    slot_responses = []
    for slot in available_slots:
        slot_responses.append(TimeSlot(
            start_time=slot['start_time'],
            end_time=slot['end_time'],
            collaborator_id=slot['collaborator_id'],
            collaborator_name=slot['collaborator_name'],
            available_minutes=slot['available_minutes']
        ))
    
    return AvailableSlotsResponse(
        date=date,
        service_id=service_id,
        service_duration=service.duration_minutes,
        available_slots=slot_responses,
        total_slots=len(slot_responses)
    )


@router.post("/{appointment_id}/confirm", response_model=AppointmentRead)
async def confirm_appointment(
    appointment_id: int,
    db: Session = Depends(get_db)
):
    """
    Confirma una cita programada.
    
    Args:
        appointment_id: ID de la cita a confirmar
        db: Sesión de base de datos
    
    Returns:
        AppointmentRead: La cita confirmada
    
    Raises:
        HTTPException: Si la cita no existe o no está en estado programado
    """
    
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cita con ID {appointment_id} no encontrada"
        )
    
    if appointment.status != AppointmentStatus.SCHEDULED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden confirmar citas en estado 'scheduled'"
        )
    
    appointment.status = AppointmentStatus.CONFIRMED
    db.commit()
    db.refresh(appointment)
    
    return appointment


@router.post("/{appointment_id}/complete", response_model=AppointmentRead)
async def complete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db)
):
    """
    Marca una cita como completada.
    
    Args:
        appointment_id: ID de la cita a completar
        db: Sesión de base de datos
    
    Returns:
        AppointmentRead: La cita completada
    
    Raises:
        HTTPException: Si la cita no existe o no está en estado confirmado
    """
    
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cita con ID {appointment_id} no encontrada"
        )
    
    if appointment.status != AppointmentStatus.CONFIRMED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden completar citas en estado 'confirmed'"
        )
    
    appointment.status = AppointmentStatus.COMPLETED
    db.commit()
    db.refresh(appointment)
    
    return appointment


@router.get("/stats/summary")
async def get_appointments_summary(
    date_from: Optional[datetime] = Query(None, description="Fecha de inicio"),
    date_to: Optional[datetime] = Query(None, description="Fecha de fin"),
    db: Session = Depends(get_db)
):
    """
    Obtiene estadísticas de las citas.
    
    Args:
        date_from: Fecha de inicio del rango
        date_to: Fecha de fin del rango
        db: Sesión de base de datos
    
    Returns:
        dict: Resumen con estadísticas
    """
    
    query = db.query(Appointment)
    
    if date_from:
        query = query.filter(Appointment.start_time >= date_from)
    
    if date_to:
        query = query.filter(Appointment.start_time <= date_to)
    
    total_appointments = query.count()
    scheduled_count = query.filter(Appointment.status == AppointmentStatus.SCHEDULED).count()
    confirmed_count = query.filter(Appointment.status == AppointmentStatus.CONFIRMED).count()
    completed_count = query.filter(Appointment.status == AppointmentStatus.COMPLETED).count()
    cancelled_count = query.filter(Appointment.status == AppointmentStatus.CANCELLED).count()
    
    return {
        "total_appointments": total_appointments,
        "scheduled": scheduled_count,
        "confirmed": confirmed_count,
        "completed": completed_count,
        "cancelled": cancelled_count,
        "completion_rate": round((completed_count / total_appointments * 100) if total_appointments > 0 else 0, 2)
    }
