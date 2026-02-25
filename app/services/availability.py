import pytz
from datetime import datetime, timedelta, time
from typing import List, Optional, Tuple, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.appointments import Appointment, AppointmentStatus
from app.models.business_hours import BusinessHours, TimeSlot
from app.models.collaborators import Collaborator
from app.models.services import Service
from app.core.settings import settings
from datetime import date

# --- CONSTANTES ---
SLOT_INTERVAL_MINUTES = 15

# Funcion para obtener el rango de horario laboral

def get_business_day_range(db: Session, day_of_week: int):
    """
    Obtiene la hora de apertura más temprana y de cierre más tardía 
    entre todos los colaboradores para un día específico.
    """
    range_data = db.query(
        func.min(TimeSlot.start_time).label("opening"),
        func.max(TimeSlot.end_time).label("closing")
    ).join(BusinessHours).filter(
        BusinessHours.day_of_week == day_of_week,
        BusinessHours.is_enabled == True
    ).first()

    return range_data.opening, range_data.closing

# --- FUNCIONES PRINCIPALES ---

def find_available_collaborator(
    db: Session, start_time: datetime, end_time: datetime, service_id: int
) -> Optional[int]:
    """
    Busca automáticamente un colaborador disponible. 
    Gracias al orden de get_available_slots, devolverá primero al especialista único.
    """
    available_slots = get_available_slots(db, start_time, service_id)

    for slot in available_slots:
        # Normalizamos para comparar sin TZs si fuera necesario
        slot_st = slot["start_time"].replace(tzinfo=None) if slot["start_time"].tzinfo else slot["start_time"]
        req_st = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
        
        if slot_st == req_st:
            return slot["collaborator_id"]

    return None


def get_available_slots(
    db: Session,
    target_date: datetime | date, # Aceptamos ambos tipos
    service_id: int,
    collaborator_id: Optional[int] = None,
    min_time: Optional[time] = None,
) -> List[dict]:
    """
    Obtiene huecos disponibles con prioridad para colaboradores especializados.
    """
    service = (
        db.query(Service)
        .filter(Service.id == service_id, Service.is_active == True)
        .first()
    )
    if not service:
        return []

    # --- FIX DE ROBUSTEZ ---
    # Si target_date es datetime, sacamos el date. Si ya es date, lo usamos tal cual.
    # Esto evita el error: 'datetime.date' object has no attribute 'date'
    pure_date = target_date.date() if isinstance(target_date, datetime) else target_date
    # -----------------------

    day_of_week = pure_date.weekday() # Usamos pure_date

    # 1. Obtener horarios y colaboradores aptos
    query = (
        db.query(BusinessHours)
        .join(Collaborator)
        .filter(
            and_(
                BusinessHours.day_of_week == day_of_week,
                BusinessHours.is_enabled == True,
                Collaborator.is_active == True,
                Collaborator.departments.any(id=service.department_id),
            )
        )
    )

    if collaborator_id:
        query = query.filter(BusinessHours.collaborator_id == collaborator_id)

    schedules = query.all()
    if not schedules:
        return []

    colab_priority_map = {}
    for s in schedules:
        is_exclusive = len(s.collaborator.departments) == 1
        colab_priority_map[s.collaborator_id] = 0 if is_exclusive else 1

    # 3. BATCH LOADING DE CITAS (Usando pure_date)
    colab_ids = [s.collaborator_id for s in schedules]
    start_of_day = datetime.combine(pure_date, time.min)
    end_of_day = datetime.combine(pure_date, time.max)

    all_appointments = (
        db.query(Appointment)
        .filter(
            and_(
                Appointment.collaborator_id.in_(colab_ids),
                Appointment.start_time < end_of_day,
                Appointment.end_time > start_of_day,
                Appointment.status.in_(
                    [
                        AppointmentStatus.SCHEDULED,
                        AppointmentStatus.CONFIRMED,
                        AppointmentStatus.IN_PROGRESS,
                    ]
                ),
            )
        )
        .all()
    )

    appointments_by_colab: Dict[int, List[Appointment]] = {}
    for apt in all_appointments:
        appointments_by_colab.setdefault(apt.collaborator_id, []).append(apt)

    # 4. GENERACIÓN DE SLOTS (Usando pure_date)
    all_raw_slots = []
    for schedule in schedules:
        colab_apts = appointments_by_colab.get(schedule.collaborator_id, [])
        for time_slot in schedule.time_slots:
            # Aquí también usamos pure_date
            slot_start_boundary = datetime.combine(pure_date, time_slot.start_time)
            slot_end_boundary = datetime.combine(pure_date, time_slot.end_time)

            slots = _generate_slots_in_range(
                slot_start_boundary,
                slot_end_boundary,
                colab_apts,
                service.duration_minutes,
                schedule.collaborator,
            )
            
            priority = colab_priority_map[schedule.collaborator_id]
            for slot in slots:
                slot["priority"] = priority
            
            all_raw_slots.extend(slots)

    # 5. ORDENACIÓN CRÍTICA: 1º por Hora, 2º por Prioridad
    # Esto asegura que el frontend reciba al mejor candidato primero para cada hora.
    all_raw_slots.sort(key=lambda x: (x["start_time"], x["priority"]))

    if min_time:
        all_raw_slots = [s for s in all_raw_slots if s["start_time"].time() >= min_time]

    return all_raw_slots


def is_valid_appointment_time(
    db: Session, collaborator_id: int, start_time: datetime, end_time: datetime
) -> Tuple[bool, str]:
    """Valida disponibilidad antes de persistir la cita."""
    tz = pytz.timezone(settings.APP_TIMEZONE)
    now = datetime.now(tz).replace(tzinfo=None)
    st_naive = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
    et_naive = end_time.replace(tzinfo=None) if end_time.tzinfo else end_time

    if st_naive < now:
        return False, "No puedes reservar en el pasado."

    day_idx = st_naive.weekday()
    schedule = (
        db.query(BusinessHours)
        .filter(
            and_(
                BusinessHours.collaborator_id == collaborator_id,
                BusinessHours.day_of_week == day_idx,
                BusinessHours.is_enabled == True,
            )
        )
        .first()
    )

    if not schedule:
        return False, "El profesional no trabaja este día."

    in_working_hours = False
    for ts in schedule.time_slots:
        ts_start = datetime.combine(st_naive.date(), ts.start_time)
        ts_end = datetime.combine(st_naive.date(), ts.end_time)
        if st_naive >= ts_start and et_naive <= ts_end:
            in_working_hours = True
            break

    if not in_working_hours:
        return False, "Fuera del horario laboral del profesional."

    if check_appointment_conflict(db, collaborator_id, st_naive, et_naive):
        return False, "El horario ya está ocupado por otra cita."

    return True, "Disponible"


def check_appointment_conflict(
    db: Session,
    collaborator_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_appointment_id: Optional[int] = None,
) -> bool:
    """Verifica si hay solapamientos en la base de datos."""
    st = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
    et = end_time.replace(tzinfo=None) if end_time.tzinfo else end_time

    query = db.query(Appointment).filter(
        and_(
            Appointment.collaborator_id == collaborator_id,
            Appointment.status.in_(
                [
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.CONFIRMED,
                    AppointmentStatus.IN_PROGRESS,
                ]
            ),
            Appointment.start_time < et,
            Appointment.end_time > st,
        )
    )
    if exclude_appointment_id:
        query = query.filter(Appointment.id != exclude_appointment_id)
    return query.first() is not None


# --- HELPERS INTERNOS ---

def _generate_slots_in_range(
    slot_start, slot_end, existing_appointments, service_duration, collaborator
):
    available_slots = []
    current_time = slot_start
    occupied = []
    
    for apt in existing_appointments:
        apt_st = apt.start_time.replace(tzinfo=None)
        apt_et = apt.end_time.replace(tzinfo=None)
        # Solo considerar citas que caigan dentro del rango de este turno
        if apt_st < slot_end and apt_et > slot_start:
            occupied.append((max(apt_st, slot_start), min(apt_et, slot_end)))

    occupied.sort(key=lambda x: x[0])

    for occ_start, occ_end in occupied:
        if current_time < occ_start:
            if (occ_start - current_time).total_seconds() / 60 >= service_duration:
                available_slots.extend(
                    _create_discrete_time_points(
                        current_time, occ_start, service_duration, collaborator
                    )
                )
        current_time = max(current_time, occ_end)

    if current_time < slot_end:
        if (slot_end - current_time).total_seconds() / 60 >= service_duration:
            available_slots.extend(
                _create_discrete_time_points(
                    current_time, slot_end, service_duration, collaborator
                )
            )
    return available_slots


def _create_discrete_time_points(start_time, end_time, service_duration, collaborator):
    slots = []
    current_pos = start_time
    tz = pytz.timezone(settings.APP_TIMEZONE)
    # Obtenemos el "ahora" sin TZ para comparar con objetos naive de la DB
    now = datetime.now(tz).replace(tzinfo=None)
    
    while current_pos + timedelta(minutes=service_duration) <= end_time:
        if current_pos > now:
            slots.append(
                {
                    "start_time": current_pos,
                    "end_time": current_pos + timedelta(minutes=service_duration),
                    "collaborator_id": collaborator.id,
                    "collaborator_name": collaborator.name,
                    "available_minutes": service_duration,
                }
            )
        current_pos += timedelta(minutes=SLOT_INTERVAL_MINUTES)
    return slots