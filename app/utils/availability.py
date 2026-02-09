"""
Utilidades para cálculo de disponibilidad y huecos libres.
Este módulo contiene la lógica para evitar conflictos de horarios en las reservas.
"""

import pytz
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.appointments import Appointment, AppointmentStatus
from app.models.business_hours import BusinessHours, TimeSlot
from app.models.collaborators import Collaborator
from app.models.services import Service
from app.core.settings import settings

# Configuración de zona horaria del negocio
BUSINESS_TZ = pytz.timezone(settings.APP_TIMEZONE)


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
    
    # Asegurar que target_date esté en la zona horaria del negocio
    if target_date.tzinfo is None:
        target_date_local = BUSINESS_TZ.localize(target_date)
    else:
        target_date_local = target_date.astimezone(BUSINESS_TZ)
    
    # 1. Validar que el servicio exista y obtener su duración
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise ValueError(f"Servicio con ID {service_id} no encontrado")
    
    if not service.is_active:
        raise ValueError(f"Servicio {service.name} no está activo")
    
    service_duration = service.duration_minutes
    
    # 2. Obtener el día de la semana (0=Lunes, 6=Domingo)
    day_of_week = target_date_local.weekday()
    
    # 3. Obtener los horarios de negocio para ese día
    business_hours = db.query(BusinessHours).filter(
        and_(
            BusinessHours.day_of_week == day_of_week,
            BusinessHours.is_enabled == True
        )
    ).first()
    
    if not business_hours:
        return []
    
    # 4. Obtener colaboradores activos (filtrar por ID específico si se proporciona)
    collaborators_query = db.query(Collaborator).filter(Collaborator.is_active == True)
    if collaborator_id:
        collaborators_query = collaborators_query.filter(Collaborator.id == collaborator_id)
    
    collaborators = collaborators_query.all()
    
    if not collaborators:
        return []
    
    # 5. Para cada colaborador, calcular sus huecos disponibles
    all_available_slots = []
    
    for collaborator in collaborators:
        # 5.1 Obtener citas existentes para ese colaborador en esa fecha
        start_of_day = BUSINESS_TZ.localize(
            datetime.combine(target_date_local.date(), datetime.min.time())
        )
        end_of_day = BUSINESS_TZ.localize(
            datetime.combine(target_date_local.date(), datetime.max.time())
        )
        
        existing_appointments = db.query(Appointment).filter(
            and_(
                Appointment.collaborator_id == collaborator.id,
                Appointment.start_time < end_of_day,
                Appointment.end_time > start_of_day,
                Appointment.status.in_([
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.CONFIRMED,
                    AppointmentStatus.IN_PROGRESS
                ])
            )
        ).order_by(Appointment.start_time).all()
        
        # 5.2 Procesar cada slot de tiempo del horario de negocio
        for time_slot in business_hours.time_slots:
            # Convertir time objects a datetime objects en la zona del negocio
            slot_start_time = BUSINESS_TZ.localize(
                datetime.combine(target_date_local.date(), time_slot.start_time)
            )
            slot_end_time = BUSINESS_TZ.localize(
                datetime.combine(target_date_local.date(), time_slot.end_time)
            )
            
            # 5.3 Generar huecos disponibles en este slot
            slots_in_time_slot = generate_slots_in_range(
                slot_start_time, 
                slot_end_time, 
                existing_appointments, 
                service_duration,
                collaborator
            )
            
            # 5.4 Agregar información del colaborador a cada hueco
            for slot in slots_in_time_slot:
                slot.update({
                    'collaborator_id': collaborator.id,
                    'collaborator_name': collaborator.name
                })
                all_available_slots.append(slot)
    
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
    
    # Convertir appointments a intervalos de tiempo ocupados (ya están en BUSINESS_TZ)
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
    Valida que una cita cumpla todas las reglas de negocio.
    
    Esta función centraliza toda la validación de horarios:
    1. Verifica que el colaborador exista y esté activo
    2. Verifica que la cita no sea en el pasado
    3. Verifica que esté dentro de horarios de negocio
    4. Verifica que no haya conflictos con otras citas
    
    Args:
        db: Sesión de base de datos
        collaborator_id: ID del colaborador
        start_time: Inicio de la cita (con timezone)
        end_time: Fin de la cita (con timezone)
    
    Returns:
        Tuple[bool, str]: (es_válido, mensaje_error)
    """
    
    # 1. Verificar que el colaborador exista y esté activo
    collaborator = db.query(Collaborator).filter(
        and_(
            Collaborator.id == collaborator_id,
            Collaborator.is_active == True
        )
    ).first()
    
    if not collaborator:
        return False, f"Colaborador con ID {collaborator_id} no encontrado o no está activo"
    
    # 2. Asegurar que las fechas estén en la zona horaria del negocio
    now_business = datetime.now(BUSINESS_TZ)
    
    # Convertir start_time y end_time a la zona del negocio si no la tienen
    if start_time.tzinfo is None:
        start_time_local = BUSINESS_TZ.localize(start_time)
    else:
        start_time_local = start_time.astimezone(BUSINESS_TZ)
    
    if end_time.tzinfo is None:
        end_time_local = BUSINESS_TZ.localize(end_time)
    else:
        end_time_local = end_time.astimezone(BUSINESS_TZ)
    
    # 3. Verificar que la cita no sea en el pasado
    if start_time_local < now_business:
        return False, "No se pueden programar citas en el pasado"
    
    # 4. Verificar horario de negocio
    day_of_week = start_time_local.weekday()
    business_hours = db.query(BusinessHours).filter(
        and_(
            BusinessHours.day_of_week == day_of_week,
            BusinessHours.is_enabled == True
        )
    ).first()
    
    if not business_hours:
        return False, f"No hay horarios de negocio disponibles para el día {start_time_local.strftime('%A')}"
    
    # 5. Verificar que la cita esté dentro de algún slot de tiempo
    is_within_business_hours = False
    for time_slot in business_hours.time_slots:
        # Convertir time objects a datetime objects en la zona del negocio
        slot_start_time = BUSINESS_TZ.localize(
            datetime.combine(start_time_local.date(), time_slot.start_time)
        )
        slot_end_time = BUSINESS_TZ.localize(
            datetime.combine(start_time_local.date(), time_slot.end_time)
        )
        
        if start_time_local >= slot_start_time and end_time_local <= slot_end_time:
            is_within_business_hours = True
            break
    
    if not is_within_business_hours:
        return False, "La hora seleccionada está fuera del horario de negocio"
    
    # 6. Verificar conflictos con otras citas
    has_conflict = check_appointment_conflict(db, collaborator_id, start_time_local, end_time_local)
    if has_conflict:
        return False, f"El colaborador {collaborator.name} ya tiene una cita programada en ese horario"
    
    return True, "Horario válido"
