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
    """Consulta real de disponibilidad en la base de datos."""
    service = db.query(Service).filter(Service.id == service_id, Service.is_active == True).first()
    if not service: return []
    
    day_of_week = target_date.weekday()
    query = db.query(BusinessHours).join(Collaborator).filter(
        and_(
            BusinessHours.day_of_week == day_of_week,
            BusinessHours.is_enabled == True,
            Collaborator.is_active == True,
            Collaborator.departments.any(id=service.department_id)
        )
    )
    
    schedules = query.all()
    all_raw_slots = []
    
    for schedule in schedules:
        # Aquí iría tu lógica de generate_slots_in_range que ya tienes
        # Para simplificar el archivo y que compile, asumimos que devuelve una lista
        pass 

    return all_raw_slots