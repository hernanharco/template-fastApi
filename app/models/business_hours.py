"""
Modelos SQLAlchemy para la gestión de horarios de negocio.
Este modelo maneja la lógica de horarios con soporte para turnos partidos y múltiples rangos de tiempo.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class BusinessHours(Base):
    """
    Modelo principal para configuración de horarios por día.
    
    Este modelo almacena la configuración general de horarios para cada día de la semana:
    - Día de la semana (Lunes, Martes, etc.)
    - Estado activo/inactivo del día
    - Configuración de turno partido
    - Relación con los slots de tiempo específicos
    """
    
    __tablename__ = "business_hours"
    
    # ID único para cada configuración de día
    id = Column(Integer, primary_key=True, index=True, comment="Identificador único de la configuración de horario")
    
    # Día de la semana (0=Lunes, 1=Martes, ..., 6=Domingo)
    day_of_week = Column(Integer, nullable=False, unique=True, comment="Día de la semana (0=Lunes, 6=Domingo)")
    
    # Nombre del día en español para facilitar la visualización
    day_name = Column(String(20), nullable=False, comment="Nombre del día (Lunes, Martes, etc.)")
    
    # Indica si el día está habilitado para trabajar
    is_enabled = Column(Boolean, default=True, nullable=False, comment="Indica si el día está habilitado para trabajo")
    
    # Indica si el día tiene turno partido (dos rangos de tiempo separados)
    is_split_shift = Column(Boolean, default=False, nullable=False, comment="Indica si el día tiene turno partido")
    
    # Timestamps para auditoría
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Fecha de creación")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Fecha de última actualización")
    
    # Relación uno-a-muchos con los slots de tiempo
    # Cuando se elimina un BusinessHours, se eliminan en cascada sus TimeSlots
    time_slots = relationship("TimeSlot", back_populates="business_hours", cascade="all, delete-orphan")
    
    def __repr__(self):
        """Representación en string del objeto BusinessHours."""
        return f"<BusinessHours(id={self.id}, day='{self.day_name}', enabled={self.is_enabled}, split={self.is_split_shift})>"
    
    def to_dict(self):
        """Convierte el objeto a un diccionario incluyendo sus time_slots."""
        return {
            "id": self.id,
            "day_of_week": self.day_of_week,
            "day_name": self.day_name,
            "is_enabled": self.is_enabled,
            "is_split_shift": self.is_split_shift,
            "time_slots": [slot.to_dict() for slot in self.time_slots],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class TimeSlot(Base):
    """
    Modelo para los rangos de tiempo específicos (slots).
    
    Este modelo almacena los rangos de tiempo individuales:
    - Hora de inicio y fin
    - Orden del slot (para turnos partidos: 1=morning, 2=afternoon)
    - Relación con el día de la semana correspondiente
    """
    
    __tablename__ = "time_slots"
    
    # ID único para cada slot de tiempo
    id = Column(Integer, primary_key=True, index=True, comment="Identificador único del slot de tiempo")
    
    # Hora de inicio (ej: 09:00:00)
    start_time = Column(Time, nullable=False, comment="Hora de inicio del slot")
    
    # Hora de fin (ej: 13:00:00)
    end_time = Column(Time, nullable=False, comment="Hora de fin del slot")
    
    # Orden del slot (1=primer turno, 2=segundo turno)
    # Esto es útil para identificar los slots en turnos partidos
    slot_order = Column(Integer, nullable=False, default=1, comment="Orden del slot (1=primero, 2=segundo)")
    
    # Clave foránea que relaciona con BusinessHours
    business_hours_id = Column(Integer, ForeignKey("business_hours.id", ondelete="CASCADE"), nullable=False, comment="ID del día de la semana asociado")
    
    # Timestamps para auditoría
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Fecha de creación")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Fecha de última actualización")
    
    # Relación muchos-a-uno con BusinessHours
    business_hours = relationship("BusinessHours", back_populates="time_slots")
    
    def __repr__(self):
        """Representación en string del objeto TimeSlot."""
        return f"<TimeSlot(id={self.id}, start={self.start_time}, end={self.end_time}, order={self.slot_order})>"
    
    def to_dict(self):
        """Convierte el objeto a un diccionario para fácil serialización."""
        return {
            "id": self.id,
            "start_time": self.start_time.strftime("%H:%M") if self.start_time else None,
            "end_time": self.end_time.strftime("%H:%M") if self.end_time else None,
            "slot_order": self.slot_order,
            "business_hours_id": self.business_hours_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
