# app/services/appointment_service.py (o similar)
from datetime import date
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from app.models.appointments import Appointment
from app.models.services import Service

def get_appointments_by_date(db: Session, selected_date: date):
    """
    Obtiene todas las citas programadas para un día específico.
    """
    return (
        db.query(Appointment)
        .options(
            # 1. Carga el servicio
            joinedload(Appointment.service)
            # 2. Carga el departamento que está DENTRO del servicio
            .joinedload(Service.department) 
        )
        .filter(
            # Tu lógica de filtrado por fecha
            func.date(Appointment.start_time) == selected_date
        )
        .all()
    )