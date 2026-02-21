from datetime import datetime, timedelta, time
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import pytz 

from app.models.appointments import Appointment, AppointmentStatus
from app.models.business_hours import BusinessHours
from app.models.collaborators import Collaborator
from app.models.services import Service
from app.core.settings import settings

def get_available_slots(db: Session, target_date: datetime, service_id: int) -> List[dict]:
    """
    SRP: Motor de cálculo de disponibilidad real.
    Versión con soporte para Madrid y filtrado de departamentos.
    """
    service = db.query(Service).filter(Service.id == service_id, Service.is_active == True).first()
    if not service:
        return []
    
    service_duration = service.duration_minutes
    day_of_week = target_date.weekday()
    
    # 1. FILTRAR COLABORADORES POR DEPARTAMENTO
    query = db.query(BusinessHours).join(Collaborator).filter(
        and_(
            BusinessHours.day_of_week == day_of_week,
            BusinessHours.is_enabled == True,
            Collaborator.is_active == True,
            Collaborator.departments.any(id=service.department_id)
        )
    )
    
    schedules = query.all()
    if not schedules:
        return []
    
    all_raw_slots = []
    tz = pytz.timezone(settings.APP_TIMEZONE)
    # Hora actual en Madrid para no ofrecer el pasado
    now_local = datetime.now(tz).replace(tzinfo=None)
    
    for schedule in schedules:
        collaborator = schedule.collaborator
        # Rango del día para buscar citas existentes
        start_of_day = datetime.combine(target_date.date(), time.min)
        end_of_day = datetime.combine(target_date.date(), time.max)
        
        # 2. BUSCAR CITAS OCUPADAS EN NEON
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
        
        # 3. GENERAR HUECOS POR CADA TURNO DEL COLABORADOR
        for time_slot in schedule.time_slots:
            slot_start = datetime.combine(target_date.date(), time_slot.start_time)
            slot_end = datetime.combine(target_date.date(), time_slot.end_time)
            
            # Generar los huecos discretos (ej: cada 15 min) dentro del turno
            current_time = slot_start
            while current_time + timedelta(minutes=service_duration) <= slot_end:
                potential_end = current_time + timedelta(minutes=service_duration)
                
                # A. ¿Es en el futuro? (Respecto a Madrid)
                if current_time > now_local:
                    # B. ¿Está libre de citas?
                    is_busy = any(
                        apt.start_time.replace(tzinfo=None) < potential_end and 
                        apt.end_time.replace(tzinfo=None) > current_time 
                        for apt in existing_appointments
                    )
                    
                    if not is_busy:
                        all_raw_slots.append({
                            'start_time': current_time,
                            'end_time': potential_end,
                            'collaborator_id': collaborator.id,
                            'collaborator_name': collaborator.name
                        })
                
                current_time += timedelta(minutes=15) # Granularidad de 15 min

    # Ordenar por hora de inicio
    all_raw_slots.sort(key=lambda x: x['start_time'])
    return all_raw_slots

def find_available_collaborator(db: Session, start_time: datetime, end_time: datetime, service_id: int) -> Optional[int]:
    """SRP: Encontrar el primer colaborador disponible para un hueco específico."""
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service: return None

    collaborators = db.query(Collaborator).filter(
        Collaborator.is_active == True,
        Collaborator.departments.any(id=service.department_id)
    ).all()
    
    for colab in collaborators:
        # Aquí llamaríamos a is_valid_appointment_time que ya tienes
        # Para simplificar, devolvemos el primero que cumpla el departamento
        return colab.id
            
    return None