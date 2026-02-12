"""
Modelos SQLAlchemy para la gestión de horarios de negocio y colaboradores.
Soporta horarios por colaborador y capacidad dinámica.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Time, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class BusinessHours(Base):
    """
    Modelo para configuración de horarios.
    Cada colaborador tiene su propio set de 7 días (Multi-tenant).
    """
    
    __tablename__ = "business_hours"
    
    id = Column(Integer, primary_key=True, index=True, comment="ID único de la configuración")
    
    # Hemos eliminado unique=True aquí para que la unicidad sea COMPUESTA (Día + Colaborador)
    day_of_week = Column(Integer, nullable=False, index=True, comment="Día de la semana (0=Lunes, 6=Domingo)")
    day_name = Column(String(20), nullable=False, comment="Nombre del día (Lunes, Martes, etc.)")
    
    is_enabled = Column(Boolean, default=True, nullable=False, comment="¿Está habilitado este día?")
    is_split_shift = Column(Boolean, default=False, nullable=False, comment="¿Tiene turno partido?")
    
    # --- RELACIÓN CON COLABORADOR ---
    collaborator_id = Column(
        Integer, 
        ForeignKey("collaborators.id", ondelete="CASCADE"), 
        nullable=True, 
        comment="ID del colaborador (NULL si es horario general)"
    )
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # --- RESTRICCIÓN DE UNICIDAD ---
    # Esto evita que un colaborador tenga dos configuraciones para el mismo lunes,
    # pero permite que el Colaborador A y el Colaborador B tengan su propio lunes.
    __table_args__ = (
        UniqueConstraint('day_of_week', 'collaborator_id', name='_day_collaborator_uc'),
    )

    # Relaciones
    time_slots = relationship("TimeSlot", back_populates="business_hours", cascade="all, delete-orphan")
    collaborator = relationship("Collaborator", back_populates="business_hours")
    
    def __repr__(self):
        owner = f"Colab:{self.collaborator_id}" if self.collaborator_id else "General"
        return f"<BusinessHours(id={self.id}, day='{self.day_name}', owner={owner})>"
    
    def to_dict(self):
        """Convierte el objeto a diccionario para la API."""
        return {
            "id": self.id,
            "day_of_week": self.day_of_week,
            "day_name": self.day_name,
            "is_enabled": self.is_enabled,
            "is_split_shift": self.is_split_shift,
            "collaborator_id": self.collaborator_id,
            "time_slots": [slot.to_dict() for slot in self.time_slots],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class TimeSlot(Base):
    """
    Modelo para los rangos de tiempo específicos (slots) dentro de un día.
    """
    
    __tablename__ = "time_slots"
    
    id = Column(Integer, primary_key=True, index=True)
    start_time = Column(Time, nullable=False, comment="Hora de inicio")
    end_time = Column(Time, nullable=False, comment="Hora de fin")
    
    # 1=Mañana, 2=Tarde (en caso de turno partido)
    slot_order = Column(Integer, nullable=False, default=1)
    
    business_hours_id = Column(
        Integer, 
        ForeignKey("business_hours.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relación inversa con BusinessHours
    business_hours = relationship("BusinessHours", back_populates="time_slots")
    
    def __repr__(self):
        return f"<TimeSlot(id={self.id}, start={self.start_time}, end={self.end_time})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "start_time": self.start_time.strftime("%H:%M") if self.start_time else None,
            "end_time": self.end_time.strftime("%H:%M") if self.end_time else None,
            "slot_order": self.slot_order,
            "business_hours_id": self.business_hours_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

__table_args__ = (
        UniqueConstraint('day_of_week', 'collaborator_id', name='_day_collaborator_uc'),
    )