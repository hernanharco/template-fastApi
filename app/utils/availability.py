"""
Utilidades para cálculo de disponibilidad y huecos libres.
Este módulo contiene la lógica para evitar conflictos de horarios en las reservas.
"""

from datetime import datetime, timedelta, time
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.appointments import Appointment, AppointmentStatus
from app.models.business_hours import BusinessHours, TimeSlot
from app.models.collaborators import Collaborator
from app.models.services import Service


def get_available_slots(
    db: Session,
    target_date: datetime,
    service_id: int,
    collaborator_id: Optional[int] = None
) -> List[dict]:
    """
    Calcula los huecos libres disponibles para un servicio en una fecha específica.
    
    Esta función implementa la lógica principal para evitar conflictos de horarios:
    1. Obtiene los horarios de negocio para el día
    2. Filtra por colaboradores activos
    3. Excluye horarios ya ocupados por otras citas
    4. Genera huecos disponibles basados en la duración del servicio
    
    Args:
        db: Sesión de base de datos
        target_date: Fecha para buscar disponibilidad (solo se usa la parte de fecha)
        service_id: ID del servicio a reservar
        collaborator_id: ID específico de colaborador (opcional)
    
    Returns:
        List[dict]: Lista de huecos disponibles con información del colaborador
    """
    
    # 1. Validar que el servicio exista y obtener su duración
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise ValueError(f"Servicio con ID {service_id} no encontrado")
    
    if not service.is_active:
        raise ValueError(f"Servicio {service.name} no está activo")
    
    service_duration = service.duration_minutes
    
    # 2. Obtener el día de la semana (0=Lunes, 6=Domingo)
    day_of_week = target_date.weekday()
    
    # 3. Obtener los horarios de negocio para ese día
    business_hours = db.query(BusinessHours).filter(
        and_(
            BusinessHours.day_of_week == day_of_week,
            BusinessHours.is_enabled == True
        )
    ).first()
    
    if not business_hours:
        return []  # No hay horarios de negocio para este día
    
    # 4. Obtener colaboradores activos (filtrar por colaborador específico si se proporciona)
    collaborators_query = db.query(Collaborator).filter(Collaborator.is_active == True)
    if collaborator_id:
        collaborators_query = collaborators_query.filter(Collaborator.id == collaborator_id)
    
    available_collaborators = collaborators_query.all()
    if not available_collaborators:
        return []
    
    # 5. Para cada colaborador, calcular sus huecos disponibles
    all_available_slots = []
    
    for collaborator in available_collaborators:
        # 5.1 Obtener las citas existentes del colaborador para esa fecha
        existing_appointments = db.query(Appointment).filter(
            and_(
                Appointment.collaborator_id == collaborator.id,
                Appointment.start_time >= target_date.replace(hour=0, minute=0, second=0, microsecond=0),
                Appointment.start_time < target_date.replace(hour=23, minute=59, second=59, microsecond=999999),
                Appointment.status.in_([
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.CONFIRMED,
                    AppointmentStatus.IN_PROGRESS
                ])
            )
        ).order_by(Appointment.start_time).all()
        
        # 5.2 Procesar cada slot de tiempo del horario de negocio
        for time_slot in business_hours.time_slots:
            # Convertir string time a datetime objects
            slot_start_time = datetime.combine(target_date.date(), 
                                              datetime.strptime(time_slot.start_time, "%H:%M").time())
            slot_end_time = datetime.combine(target_date.date(), 
                                            datetime.strptime(time_slot.end_time, "%H:%M").time())
            
            # 5.3 Generar huecos disponibles en este slot
            slots_in_time_slot = generate_slots_in_range(
                slot_start_time, 
                slot_end_time, 
                existing_appointments, 
                service_duration,
                collaborator
            )
            
            all_available_slots.extend(slots_in_time_slot)
    
    # 6. Ordenar por hora de inicio
    all_available_slots.sort(key=lambda x: x['start_time'])
    
    return all_available_slots


def generate_slots_in_range(
    slot_start: datetime,
    slot_end: datetime,
    existing_appointments: List[Appointment],
    service_duration: int,
    collaborator: Collaborator
) -> List[dict]:
    """
    Genera huecos disponibles en un rango de tiempo específico.
    
    Esta es la función clave que previene conflictos:
    - Analiza las citas existentes
    - Encuentra los espacios vacíos entre ellas
    - Genera slots que no se solapan con citas existentes
    
    Args:
        slot_start: Inicio del rango de tiempo
        slot_end: Fin del rango de tiempo
        existing_appointments: Lista de citas ya programadas
        service_duration: Duración requerida para el nuevo servicio
        collaborator: Objeto del colaborador
    
    Returns:
        List[dict]: Lista de huecos disponibles en este rango
    """
    
    available_slots = []
    current_time = slot_start
    
    # Convertir appointments a intervalos de tiempo ocupados
    occupied_intervals = []
    for apt in existing_appointments:
        # Solo considerar citas que intersectan con el slot actual
        if apt.start_time < slot_end and apt.end_time > slot_start:
            occupied_intervals.append((apt.start_time, apt.end_time))
    
    # Ordenar intervalos ocupados por hora de inicio
    occupied_intervals.sort(key=lambda x: x[0])
    
    # Recorrer el slot buscando espacios libres
    for occupied_start, occupied_end in occupied_intervals:
        # Si hay espacio antes de la cita ocupada
        if current_time < occupied_start:
            # Verificar si hay suficiente tiempo para el servicio
            available_time = (occupied_start - current_time).total_seconds() / 60
            if available_time >= service_duration:
                # Generar slots dentro de este espacio libre
                slots = generate_discrete_slots(
                    current_time, 
                    occupied_start, 
                    service_duration,
                    collaborator
                )
                available_slots.extend(slots)
        
        # Mover el tiempo actual al final de la cita ocupada
        current_time = max(current_time, occupied_end)
    
    # Verificar si hay espacio después de la última cita
    if current_time < slot_end:
        available_time = (slot_end - current_time).total_seconds() / 60
        if available_time >= service_duration:
            slots = generate_discrete_slots(
                current_time, 
                slot_end, 
                service_duration,
                collaborator
            )
            available_slots.extend(slots)
    
    return available_slots


def generate_discrete_slots(
    start_time: datetime,
    end_time: datetime,
    service_duration: int,
    collaborator: Collaborator
) -> List[dict]:
    """
    Genera slots discretos dentro de un rango de tiempo libre.
    
    Args:
        start_time: Inicio del espacio libre
        end_time: Fin del espacio libre
        service_duration: Duración del servicio
        collaborator: Objeto del colaborador
    
    Returns:
        List[dict]: Lista de slots generados
    """
    
    slots = []
    current_slot_start = start_time
    
    while current_slot_start + timedelta(minutes=service_duration) <= end_time:
        slot_end = current_slot_start + timedelta(minutes=service_duration)
        
        slots.append({
            'start_time': current_slot_start,
            'end_time': slot_end,
            'collaborator_id': collaborator.id,
            'collaborator_name': collaborator.name,
            'available_minutes': int((slot_end - current_slot_start).total_seconds() / 60)
        })
        
        # Avanzar al siguiente posible slot (cada 15 minutos por defecto)
        current_slot_start += timedelta(minutes=15)
    
    return slots


def check_appointment_conflict(
    db: Session,
    collaborator_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_appointment_id: Optional[int] = None
) -> bool:
    """
    Verifica si una nueva cita tiene conflictos con citas existentes.
    
    Esta es la función de seguridad que previne dobles reservas:
    - Busca citas que se solapan en tiempo
    - Considera solo citas activas
    - Permite excluir una cita específica (para actualizaciones)
    
    Args:
        db: Sesión de base de datos
        collaborator_id: ID del colaborador
        start_time: Inicio de la nueva cita
        end_time: Fin de la nueva cita
        exclude_appointment_id: ID de cita a excluir (para actualizaciones)
    
    Returns:
        bool: True si hay conflicto, False si no hay conflicto
    """
    
    # Construir la consulta para detectar solapamientos
    conflict_query = db.query(Appointment).filter(
        and_(
            Appointment.collaborator_id == collaborator_id,
            # Solapamiento: nueva cita empieza antes de que termine otra y termina después de que empieza otra
            or_(
                and_(Appointment.start_time <= start_time, Appointment.end_time > start_time),
                and_(Appointment.start_time < end_time, Appointment.end_time >= end_time),
                and_(Appointment.start_time >= start_time, Appointment.end_time <= end_time)
            ),
            Appointment.status.in_([
                AppointmentStatus.SCHEDULED,
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.IN_PROGRESS
            ])
        )
    )
    
    # Excluir cita específica si se proporciona (para actualizaciones)
    if exclude_appointment_id:
        conflict_query = conflict_query.filter(Appointment.id != exclude_appointment_id)
    
    conflicting_appointment = conflict_query.first()
    
    return conflicting_appointment is not None


def is_valid_appointment_time(
    db: Session,
    collaborator_id: int,
    start_time: datetime,
    end_time: datetime
) -> Tuple[bool, str]:
    """
    Verifica si un horario es válido para una nueva cita.
    
    Esta función valida múltiples restricciones:
    1. Horario de negocio
    2. Conflictos con otras citas
    3. Colaborador activo
    
    Args:
        db: Sesión de base de datos
        collaborator_id: ID del colaborador
        start_time: Inicio de la cita
        end_time: Fin de la cita
    
    Returns:
        Tuple[bool, str]: (es_válido, mensaje_de_error)
    """
    
    # 1. Verificar que el colaborador existe y está activo
    collaborator = db.query(Collaborator).filter(
        and_(
            Collaborator.id == collaborator_id,
            Collaborator.is_active == True
        )
    ).first()
    
    if not collaborator:
        return False, f"Colaborador con ID {collaborator_id} no encontrado o no está activo"
    
    # 2. Verificar que la cita no sea en el pasado
    if start_time < datetime.now():
        return False, "No se pueden programar citas en el pasado"
    
    # 3. Verificar horario de negocio
    day_of_week = start_time.weekday()
    business_hours = db.query(BusinessHours).filter(
        and_(
            BusinessHours.day_of_week == day_of_week,
            BusinessHours.is_enabled == True
        )
    ).first()
    
    if not business_hours:
        return False, f"No hay horarios de negocio disponibles para el día {start_time.strftime('%A')}"
    
    # Verificar que la cita esté dentro de algún slot de tiempo
    is_within_business_hours = False
    for time_slot in business_hours.time_slots:
        slot_start_time = datetime.combine(start_time.date(), 
                                          datetime.strptime(time_slot.start_time, "%H:%M").time())
        slot_end_time = datetime.combine(start_time.date(), 
                                        datetime.strptime(time_slot.end_time, "%H:%M").time())
        
        if start_time >= slot_start_time and end_time <= slot_end_time:
            is_within_business_hours = True
            break
    
    if not is_within_business_hours:
        return False, "La hora seleccionada está fuera del horario de negocio"
    
    # 4. Verificar conflictos con otras citas
    has_conflict = check_appointment_conflict(db, collaborator_id, start_time, end_time)
    if has_conflict:
        return False, f"El colaborador {collaborator.name} ya tiene una cita programada en ese horario"
    
    return True, "Horario válido"
