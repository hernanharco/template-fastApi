# app/services/availability.py
import pytz
from datetime import datetime, timedelta, time, date
from typing import List, Optional, Tuple, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from rich import print as rprint

from app.models.appointments import Appointment, AppointmentStatus
from app.models.business_hours import BusinessHours, TimeSlot
from app.models.collaborators import Collaborator, collaborator_departments
from app.models.services import Service
from app.core.config import settings

# --- CONSTANTES ---
SLOT_INTERVAL_MINUTES = 60

# --- FUNCIONES DE APOYO ---


def get_business_day_range(db: Session, day_of_week: int):
    """SRP: Obtiene el rango total de apertura del local para un día."""
    range_data = (
        db.query(
            func.min(TimeSlot.start_time).label("opening"),
            func.max(TimeSlot.end_time).label("closing"),
        )
        .join(BusinessHours)
        .filter(
            BusinessHours.day_of_week == day_of_week, BusinessHours.is_enabled == True
        )
        .first()
    )
    return range_data.opening, range_data.closing


# --- FUNCIONES PRINCIPALES ---


def find_available_collaborator(
    db: Session,
    start_time: datetime,
    end_time: datetime,
    service_id: int,
    collaborator_id: Optional[int] = None,
) -> Optional[int]:
    """Busca un colaborador disponible. Si hay favorito, valida solo a ese."""
    rprint(
        f"[cyan]🔍 Buscando colaborador para:[/cyan] {start_time.strftime('%Y-%m-%d %H:%M')} (Servicio: {service_id})"
    )

    available_slots = get_available_slots(
        db, start_time, service_id, collaborator_id=collaborator_id
    )
    rprint(f"[cyan]📊 Slots calculados para ese día:[/cyan] {len(available_slots)}")

    # Normalización para comparar sin microsegundos
    req_st = (
        start_time.replace(tzinfo=None, second=0, microsecond=0)
        if start_time.tzinfo
        else start_time.replace(second=0, microsecond=0)
    )

    for slot in available_slots:
        slot_st = (
            slot["start_time"].replace(tzinfo=None, second=0, microsecond=0)
            if slot["start_time"].tzinfo
            else slot["start_time"].replace(second=0, microsecond=0)
        )

        if slot_st == req_st:
            rprint(
                f"[green]✅ Match encontrado:[/green] {slot['collaborator_name']} (ID: {slot['collaborator_id']})"
            )
            return slot["collaborator_id"]

    rprint(f"[red]❌ No hubo coincidencia exacta para la hora {req_st.time()}[/red]")
    return None


def get_available_slots(
    db: Session,
    target_date: datetime | date,
    service_id: int,
    collaborator_id: Optional[int] = None,
    min_time: Optional[time] = None,
) -> List[dict]:
    """Obtiene huecos disponibles usando JOIN explícito."""
    service = (
        db.query(Service)
        .filter(Service.id == service_id, Service.is_active == True)
        .first()
    )
    if not service:
        rprint(f"[red]❌ Servicio {service_id} no encontrado[/red]")
        return []

    pure_date = target_date.date() if isinstance(target_date, datetime) else target_date
    day_of_week = pure_date.weekday()

    rprint(f"[blue]🔨 Generando slots para:[/blue] {pure_date} (Día {day_of_week})")

    query = (
        db.query(BusinessHours)
        .join(Collaborator, BusinessHours.collaborator_id == Collaborator.id)
        .join(
            collaborator_departments,
            Collaborator.id == collaborator_departments.c.collaborator_id,
        )
        .filter(
            and_(
                BusinessHours.day_of_week == day_of_week,
                BusinessHours.is_enabled == True,
                Collaborator.is_active == True,
                collaborator_departments.c.department_id == service.department_id,
            )
        )
    )

    if collaborator_id:
        query = query.filter(BusinessHours.collaborator_id == collaborator_id)

    schedules = query.all()

    if not schedules:
        rprint(f"[yellow]⚠️ No hay horarios en DB para el día {day_of_week}[/yellow]")
        return []

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

    all_raw_slots = []
    for schedule in schedules:
        for time_slot in schedule.time_slots:
            # 🚀 FIX: Usar la hora real de la DB para los límites del día
            slot_start_boundary = datetime.combine(
                pure_date, time_slot.start_time
            ).replace(second=0, microsecond=0)
            slot_end_boundary = datetime.combine(pure_date, time_slot.end_time).replace(
                second=0, microsecond=0
            )

            slots = _generate_slots_in_range(
                slot_start_boundary,
                slot_end_boundary,
                appointments_by_colab.get(schedule.collaborator_id, []),
                service.duration_minutes,
                schedule.collaborator,
            )
            all_raw_slots.extend(slots)

    all_raw_slots.sort(key=lambda x: x["start_time"])
    return all_raw_slots


def is_valid_appointment_time(
    db: Session, collaborator_id: int, start_time: datetime, end_time: datetime
) -> Tuple[bool, str]:
    """Verifica solapamientos con precisión de minutos."""
    tz = pytz.timezone(settings.APP_TIMEZONE)
    now_local = datetime.now(tz)

    # 🚀 FIX CRÍTICO: Asegurar que ambas fechas sean timezone-aware
    if start_time.tzinfo is None:
        start_time = tz.localize(start_time)
    if end_time.tzinfo is None:
        end_time = tz.localize(end_time)

    # Normalización para comparar (mantener timezone)
    st = start_time.replace(second=0, microsecond=0)
    et = end_time.replace(second=0, microsecond=0)

    rprint(
        f"[magenta]🧪 Validando:[/magenta] {st.strftime('%Y-%m-%d %H:%M')} (Colab: {collaborator_id})"
    )

    # ERROR DETECTADO EN LOGS: Comparación con el pasado
    if start_time < now_local:
        rprint(
            f"[red]❌ RECHAZADO: {st} es anterior a {now_local.strftime('%Y-%m-%d %H:%M')}[/red]"
        )
        return False, "No puedes reservar en el pasado."

    day_idx = st.weekday()
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
        rprint(f"[yellow]⚠️ RECHAZADO: Sin horario para día {day_idx}[/yellow]")
        return False, f"El profesional no trabaja el día {day_idx}."

    req_time_start = st.time()
    req_time_end = et.time()

    in_working_hours = False
    for ts in schedule.time_slots:
        db_start = ts.start_time.replace(second=0, microsecond=0)
        db_end = ts.end_time.replace(second=0, microsecond=0)

        rprint(f"[magenta]   -> Slot DB:[/magenta] {db_start} - {db_end}")

        if req_time_start >= db_start and req_time_end <= db_end:
            in_working_hours = True
            rprint("[green]   ✅ Horario OK[/green]")
            break

    if not in_working_hours:
        rprint(f"[red]❌ RECHAZADO: {req_time_start} fuera de jornada[/red]")
        return False, "Fuera del horario laboral."

    if check_appointment_conflict(db, collaborator_id, st, et):
        rprint("[red]❌ RECHAZADO: Conflicto con otra cita[/red]")
        return False, "El horario ya está ocupado por otra cita."

    rprint("[green]✨ DISPONIBLE[/green]")
    return True, "Disponible"


def check_appointment_conflict(
    db: Session,
    collaborator_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_appointment_id: Optional[int] = None,
) -> bool:
    """Verifica solapamientos con precisión de minutos."""
    st = start_time.replace(tzinfo=None, second=0, microsecond=0)
    et = end_time.replace(tzinfo=None, second=0, microsecond=0)

    conflict = (
        db.query(Appointment)
        .filter(
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
        .first()
    )
    return conflict is not None


# --- HELPERS INTERNOS ---


def _generate_slots_in_range(
    slot_start, slot_end, existing_appointments, service_duration, collaborator
):
    available_slots = []
    current_time = slot_start
    occupied = []

    for apt in existing_appointments:
        apt_st = apt.start_time.replace(tzinfo=None, second=0, microsecond=0)
        apt_et = apt.end_time.replace(tzinfo=None, second=0, microsecond=0)
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
    current_pos = start_time.replace(second=0, microsecond=0)
    tz = pytz.timezone(settings.APP_TIMEZONE)
    now = datetime.now(tz).replace(tzinfo=None, second=0, microsecond=0)

    # 🎯 INTERVALO MEJORADO: 60 minutos entre slots en lugar de 15
    slot_interval = max(60, service_duration + 30)  # Mínimo 1 hora entre citas

    while current_pos + timedelta(minutes=service_duration) <= end_time:
        # 🚀 Seguridad: Solo slots futuros
        if current_pos >= now:
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
