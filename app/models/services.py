"""
Modelo SQLAlchemy para la gestión de servicios.
Este modelo representa los servicios que ofrece el negocio (ej: manicura, pedicura, etc.).
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base


class Service(Base):
    """
    Modelo de Service para la tabla de servicios.
    
    Este modelo almacena información sobre los servicios disponibles:
    - Nombre del servicio
    - Duración en minutos
    - Precio del servicio
    - Fechas de creación y actualización
    - Estado activo/inactivo
    """
    
    __tablename__ = "services"
    
    # ID único para cada servicio
    id = Column(Integer, primary_key=True, index=True, comment="Identificador único del servicio")
    
    # Nombre del servicio (ej: "Manicura", "Pedicura", "Tratamiento facial")
    name = Column(String(100), nullable=False, comment="Nombre descriptivo del servicio")
    
    # Duración en minutos (ej: 30, 60, 90)
    duration_minutes = Column(Integer, nullable=False, comment="Duración del servicio en minutos")
    
    # Precio del servicio (ej: 150.00, 300.50)
    price = Column(Float, nullable=False, comment="Precio del servicio")
    
    # Control de estado: si el servicio está activo o no
    is_active = Column(Boolean, default=True, nullable=False, comment="Indica si el servicio está activo")
    
    # Timestamps automáticos para auditoría
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Fecha de creación")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Fecha de última actualización")
    
    # Relación uno-a-muchos con appointments
    appointments = relationship("Appointment", back_populates="service", cascade="all, delete-orphan")
    
    def __repr__(self):
        """Representación en string del objeto Service."""
        return f"<Service(id={self.id}, name='{self.name}', duration={self.duration_minutes}min, price=${self.price})>"
    
    def to_dict(self):
        """Convierte el objeto a un diccionario para fácil serialización."""
        return {
            "id": self.id,
            "name": self.name,
            "duration_minutes": self.duration_minutes,
            "price": self.price,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
