"""
Utilidades para cálculo de disponibilidad y huecos libres.
Versión NAIVE: Sin zonas horarias para evitar desfases en la base de datos.
"""

from datetime import datetime, timedelta, time
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.appointments import Appointment, AppointmentStatus
from app.models.business_hours import BusinessHours
from app.models.collaborators import Collaborator
from app.models.services import Service
from app.core.settings import settings
import pytz 

def get_available_slots(
    db: Session,
    target_date: datetime,
    service_id: int,
    collaborator_id: Optional[int] = None
) -> List[dict]:
    """
    Calcula huecos libres. Si collaborator_id es None, devuelve todos los slots
    de todos los profesionales disponibles.
    """
    service = db.query(Service).filter(Service.id == service_id, Service.is_active == True).first()
    if not service:
        return []
    
    service_duration = service.duration_minutes
    day_of_week = target_date.weekday()
    
    # 1. Buscamos los horarios configurados
    query = db.query(BusinessHours).join(Collaborator).filter(
        and_(
            BusinessHours.day_of_week == day_of_week,
            BusinessHours.is_enabled == True,
            Collaborator.is_active == True
        )
    )

    active_collaborators = db.query(Collaborator).filter(Collaborator.is_active == True).all()
    
    if collaborator_id:
        query = query.filter(BusinessHours.collaborator_id == collaborator_id)
    
    schedules = query.all()
    if not schedules:
        return []
    
    all_raw_slots = []
    
    # 2. Generamos slots por cada colaborador/horario
    for schedule in schedules:
        collaborator = schedule.collaborator
        # Fechas límite del día (NAIVE) para filtrar citas
        start_of_day = datetime.combine(target_date.date(), time.min)
        end_of_day = datetime.combine(target_date.date(), time.max)
        
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
        
        for time_slot in schedule.time_slots:
            # Combinamos fecha y hora sin aplicar zonas horarias (Naive)
            slot_start_time = datetime.combine(target_date.date(), time_slot.start_time)
            slot_end_time = datetime.combine(target_date.date(), time_slot.end_time)
            
            slots = generate_slots_in_range(
                slot_start_time, 
                slot_end_time, 
                existing_appointments, 
                service_duration,
                collaborator
            )
            all_raw_slots.extend(slots)

    # Ordenamos cronológicamente
    all_raw_slots.sort(key=lambda x: x['start_time'])
    return all_raw_slots

def find_available_collaborator(
    db: Session,
    start_time: datetime,
    end_time: datetime,
    service_id: int
) -> Optional[int]:
    """
    Busca al primer colaborador disponible para una hora específica.
    Asegura que las fechas sean Naive antes de validar.
    """
    # Limpiamos zona horaria por si acaso
    st_naive = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
    et_naive = end_time.replace(tzinfo=None) if end_time.tzinfo else end_time

    # Buscamos colaboradores activos
    collaborators = db.query(Collaborator).filter(Collaborator.is_active == True).all()
    
    for colab in collaborators:
        # Reutilizamos la validación Naive
        is_valid, _ = is_valid_appointment_time(db, colab.id, st_naive, et_naive)
        if is_valid:
            return colab.id
            
    return None

def generate_slots_in_range(
    slot_start: datetime,
    slot_end: datetime,
    existing_appointments: List[Appointment],
    service_duration: int,
    collaborator: Collaborator
) -> List[dict]:
    available_slots = []
    current_time = slot_start
    
    occupied_intervals = []
    for apt in existing_appointments:
        # Aseguramos que las citas de la DB se traten como Naive
        apt_start = apt.start_time.replace(tzinfo=None) if apt.start_time.tzinfo else apt.start_time
        apt_end = apt.end_time.replace(tzinfo=None) if apt.end_time.tzinfo else apt.end_time
        
        if apt_start < slot_end and apt_end > slot_start:
            occupied_intervals.append((apt_start, apt_end))
    
    occupied_intervals.sort(key=lambda x: x[0])
    
    for occupied_start, occupied_end in occupied_intervals:
        if current_time < occupied_start:
            available_min = (occupied_start - current_time).total_seconds() / 60
            if available_min >= service_duration:
                slots = generate_discrete_slots(current_time, occupied_start, service_duration, collaborator)
                available_slots.extend(slots)
        current_time = max(current_time, occupied_end)
    
    if current_time < slot_end:
        available_min = (slot_end - current_time).total_seconds() / 60
        if available_min >= service_duration:
            slots = generate_discrete_slots(current_time, slot_end, service_duration, collaborator)
            available_slots.extend(slots)
    
    return available_slots

def generate_discrete_slots(
    start_time: datetime,
    end_time: datetime,
    service_duration: int,
    collaborator: Collaborator
) -> List[dict]:
    slots = []
    current_slot_start = start_time
    
    # 🕒 Obtenemos la hora actual "naive" para comparar
    tz = pytz.timezone(settings.APP_TIMEZONE)
    now = datetime.now(tz).replace(tzinfo=None)
    
    while current_slot_start + timedelta(minutes=service_duration) <= end_time:
        slot_end = current_slot_start + timedelta(minutes=service_duration)
        
        # 🚀 FILTRO CRÍTICO: Solo agregamos el hueco si es en el futuro
        if current_slot_start > now:
            slots.append({
                'start_time': current_slot_start,
                'end_time': slot_end,
                'collaborator_id': collaborator.id,
                'collaborator_name': collaborator.name,
                'available_minutes': service_duration
            })
            
        current_slot_start += timedelta(minutes=15)
    
    return slots

def is_valid_appointment_time(
    db: Session,
    collaborator_id: int,
    start_time: datetime,
    end_time: datetime
) -> Tuple[bool, str]:
    """
    Valida disponibilidad usando comparaciones Naive (sin TZ).
    """
    tz = pytz.timezone(settings.APP_TIMEZONE)
    now = datetime.now(tz).replace(tzinfo=None)
    st_naive = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
    et_naive = end_time.replace(tzinfo=None) if end_time.tzinfo else end_time

    if st_naive < now:
        return False, "No puedes reservar en el pasado."

    day_idx = st_naive.weekday()
    schedule = db.query(BusinessHours).filter(
        and_(
            BusinessHours.collaborator_id == collaborator_id,
            BusinessHours.day_of_week == day_idx,
            BusinessHours.is_enabled == True
        )
    ).first()

    if not schedule:
        return False, "El profesional no trabaja este día."

    in_slot = False
    for ts in schedule.time_slots:
        ts_start = datetime.combine(st_naive.date(), ts.start_time)
        ts_end = datetime.combine(st_naive.date(), ts.end_time)
        if st_naive >= ts_start and et_naive <= ts_end:
            in_slot = True
            break
    
    if not in_slot:
        return False, "Fuera del horario laboral."

    # Conflicto con otras citas (Comparación Naive)
    conflict = db.query(Appointment).filter(
        and_(
            Appointment.collaborator_id == collaborator_id,
            Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED, AppointmentStatus.IN_PROGRESS]),
            or_(
                and_(Appointment.start_time <= st_naive, Appointment.end_time > st_naive),
                and_(Appointment.start_time < et_naive, Appointment.end_time >= et_naive)
            )
        )
    ).first()

    if conflict:
        return False, "Horario ya ocupado."

    return True, "Disponible"

def check_appointment_conflict(
    db: Session,
    collaborator_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_appointment_id: Optional[int] = None
) -> bool:
    """
    Versión Naive del chequeo de conflictos.
    """
    tz = pytz.timezone(settings.APP_TIMEZONE)
    st = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
    et = end_time.replace(tzinfo=None) if end_time.tzinfo else end_time

    conflict_query = db.query(Appointment).filter(
        and_(
            Appointment.collaborator_id == collaborator_id,
            Appointment.status.in_([
                AppointmentStatus.SCHEDULED,
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.IN_PROGRESS
            ]),
            or_(
                and_(Appointment.start_time <= st, Appointment.end_time > st),
                and_(Appointment.start_time < et, Appointment.end_time >= et),
                and_(Appointment.start_time >= st, Appointment.end_time <= et)
            )
        )
    )
    if exclude_appointment_id:
        conflict_query = conflict_query.filter(Appointment.id != exclude_appointment_id)
    
    return conflict_query.first() is not None