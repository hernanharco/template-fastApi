"""
Modelo SQLAlchemy para el dominio de citas (appointments).
Este modelo representa las reservas de servicios con colaboradores específicos.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base

from app.models.clients import Client


class AppointmentStatus(str, enum.Enum):
    """Enumeración para los estados de las citas."""
    SCHEDULED = "scheduled"      # Programada
    CONFIRMED = "confirmed"      # Confirmada
    IN_PROGRESS = "in_progress"  # En curso
    COMPLETED = "completed"      # Completada
    CANCELLED = "cancelled"      # Cancelada
    NO_SHOW = "no_show"          # No asistió


class Appointment(Base):
    """
    Modelo de Appointment para la tabla de citas.
    """
    
    __tablename__ = "appointments"
    
    # ID único para cada cita
    id = Column(Integer, primary_key=True, index=True, comment="Identificador único de la cita")
    
    # --- RELACIONES DE LLAVE FORÁNEA (Foreign Keys) ---
    
    # 1. Relación con el Cliente (NUEVA)
    # Guardamos el ID del cliente para vincularlo a su historial
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, comment="ID del cliente vinculado")
    
    # 2. Relación con el servicio solicitado
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False, comment="ID del servicio")
    
    # 3. Relación con el colaborador asignado
    collaborator_id = Column(Integer, ForeignKey("collaborators.id", ondelete="CASCADE"), nullable=False, comment="ID del colaborador")
    
    # --- INFORMACIÓN DEL CLIENTE (Snapshot) ---
    # Nota: Mantenemos estos campos aquí para tener una copia de los datos 
    # en el momento de la reserva, por si el cliente cambia de teléfono después.
    client_name = Column(String(100), nullable=False, comment="Nombre completo del cliente")
    client_phone = Column(String(20), nullable=True, comment="Teléfono de contacto del cliente")
    client_email = Column(String(255), nullable=True, comment="Email del cliente (opcional)")
    client_notes = Column(Text, nullable=True, comment="Notas adicionales del cliente")
    
    # --- HORARIO Y ESTADO ---
    start_time = Column(DateTime(timezone=True), nullable=False, index=True, comment="Fecha y hora de inicio")
    end_time = Column(DateTime(timezone=True), nullable=False, comment="Fecha y hora de fin")
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED, nullable=False, comment="Estado actual de la cita")
    
    # --- AUDITORÍA ---
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Fecha de creación")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Fecha de última actualización")
    
    # --- RELACIONES ORM (Para acceder desde Python) ---
    # Permite hacer: appointment.client.full_name
    client = relationship("Client", back_populates="appointments")
    # Permite hacer: appointment.service.name
    service = relationship("Service", back_populates="appointments")
    # Permite hacer: appointment.collaborator.name
    collaborator = relationship("Collaborator", back_populates="appointments")

    client = relationship("Client", back_populates="appointments")
    
    def __repr__(self):
        return f"<Appointment(id={self.id}, client='{self.client_name}', start={self.start_time}, status={self.status})>"
    
    def to_dict(self):
        """Convierte el objeto a un diccionario para fácil serialización."""
        return {
            "id": self.id,
            "client_id": self.client_id,
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