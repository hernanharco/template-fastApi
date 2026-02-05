"""
Modelo SQLAlchemy para el dominio de citas (appointments).
Este modelo representa las reservas de servicios con colaboradores específicos.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base


class AppointmentStatus(str, enum.Enum):
    """Enumeración para los estados de las citas."""
    SCHEDULED = "scheduled"      # Programada
    CONFIRMED = "confirmed"      # Confirmada
    IN_PROGRESS = "in_progress"  # En curso
    COMPLETED = "completed"     # Completada
    CANCELLED = "cancelled"      # Cancelada
    NO_SHOW = "no_show"         # No asistió


class Appointment(Base):
    """
    Modelo de Appointment para la tabla de citas.
    
    Este modelo almacena información sobre las reservas:
    - Servicio solicitado
    - Colaborador asignado
    - Información del cliente
    - Horario de la cita
    - Estado actual
    """
    
    __tablename__ = "appointments"
    
    # ID único para cada cita
    id = Column(Integer, primary_key=True, index=True, comment="Identificador único de la cita")
    
    # Relación con el servicio solicitado
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False, comment="ID del servicio")
    
    # Relación con el colaborador asignado
    collaborator_id = Column(Integer, ForeignKey("collaborators.id", ondelete="CASCADE"), nullable=False, comment="ID del colaborador")
    
    # Información del cliente
    client_name = Column(String(100), nullable=False, comment="Nombre completo del cliente")
    client_phone = Column(String(20), nullable=True, comment="Teléfono de contacto del cliente")
    client_email = Column(String(255), nullable=True, comment="Email del cliente (opcional)")
    client_notes = Column(Text, nullable=True, comment="Notas adicionales del cliente")
    
    # Horario de la cita
    start_time = Column(DateTime(timezone=True), nullable=False, index=True, comment="Fecha y hora de inicio")
    end_time = Column(DateTime(timezone=True), nullable=False, comment="Fecha y hora de fin")
    
    # Estado de la cita
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED, nullable=False, comment="Estado actual de la cita")
    
    # Timestamps automáticos para auditoría
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Fecha de creación")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Fecha de última actualización")
    
    # Relaciones con otras tablas
    service = relationship("Service", back_populates="appointments")
    collaborator = relationship("Collaborator", back_populates="appointments")
    
    def __repr__(self):
        """Representación en string del objeto Appointment."""
        return f"<Appointment(id={self.id}, client='{self.client_name}', start={self.start_time}, status={self.status})>"
    
    def to_dict(self):
        """Convierte el objeto a un diccionario para fácil serialización."""
        return {
            "id": self.id,
            "service_id": self.service_id,
            "collaborator_id": self.collaborator_id,
            "client_name": self.client_name,
            "client_phone": self.client_phone,
            "client_email": self.client_email,
            "client_notes": self.client_notes,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status.value if self.status else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @property
    def duration_minutes(self):
        """Calcula la duración de la cita en minutos."""
        if self.start_time and self.end_time:
            return int((self.end_time - self.start_time).total_seconds() / 60)
        return None
    
    @property
    def is_active(self):
        """Verifica si la cita está en un estado activo (no cancelada ni completada)."""
        return self.status in [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED, AppointmentStatus.IN_PROGRESS]
