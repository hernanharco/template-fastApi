from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.models.base import Base

class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"

class AppointmentSource(str, enum.Enum):
    IA = "ia"
    MANUAL = "manual"
    WEB = "web"

class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"), nullable=False)
    collaborator_id = Column(Integer, ForeignKey("collaborators.id", ondelete="CASCADE"), nullable=False)
    
    client_name = Column(String(100), nullable=False)
    client_phone = Column(String(20), nullable=True)
    client_email = Column(String(255), nullable=True)
    client_notes = Column(Text, nullable=True)
    
    # --- CAMBIO CLAVE AQUÍ ---
    # Cambiamos Enum(AppointmentSource) por String(50).
    # Esto permite que insertes "ia" sin que Postgres se queje por tipos.
    source = Column(
        String(50), 
        default="manual", 
        nullable=False, 
        comment="Origen: ia, manual o web"
    )
    
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    client = relationship("Client", back_populates="appointments")
    service = relationship("Service", back_populates="appointments") # esta forma podemos traer la info
    collaborator = relationship("Collaborator", back_populates="appointments")

    def __repr__(self):
        return f"<Appointment(id={self.id}, source='{self.source}', status={self.status})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "source": self.source, # Al ser string, ya no necesitas .value
            "service_id": self.service_id,
            "client_name": self.client_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "status": self.status.value if self.status else None
        }