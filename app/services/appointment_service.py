from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.collaborators import Collaborator
from app.models.departments import Department
from app.models.services import Service
from app.models.appointments import Appointment # Necesitamos este para ver las ocupaciones

class AppointmentService:
    
    @staticmethod
    def get_eligible_collaborators(db: Session, service_id: int):
        # ... (este código se queda igual, es tu filtro de habilidades) ...
        service = db.query(Service).filter(Service.id == service_id).first()
        if not service: return []
        
        return db.query(Collaborator).join(Collaborator.departments).filter(
            Department.id == service.department_id,
            Collaborator.is_active == True
        ).all()

    @staticmethod
    def get_available_collaborators(db: Session, service_id: int, start_time: datetime):
        """
        NUEVO MÉTODO:
        Filtra los colaboradores que tienen la habilidad Y están libres a esa hora.
        """
        # 1. Obtenemos el servicio para saber cuánto dura
        service = db.query(Service).filter(Service.id == service_id).first()
        if not service:
            return []
        
        end_time = start_time + timedelta(minutes=service.duration_minutes)

        # 2. Primero, vemos quiénes TIENEN LA HABILIDAD (Elianac y Hernanc para cabello)
        eligible = AppointmentService.get_eligible_collaborators(db, service_id)
        
        available = []

        for colab in eligible:
            # 3. REGLA DE ORO: ¿Tiene este colaborador alguna cita que se cruce?
            # Buscamos citas que empiecen antes de que termine esta, 
            # y terminen después de que esta empiece.
            collision = db.query(Appointment).filter(
                Appointment.collaborator_id == colab.id,
                Appointment.status != 'cancelled',
                Appointment.start_time < end_time,
                Appointment.end_time > start_time
            ).first()

            if not collision:
                available.append(colab)
                
        return available