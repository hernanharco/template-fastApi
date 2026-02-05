"""
Modelo SQLAlchemy para el dominio de colaboradores.
Este modelo representa a los colaboradores que trabajan en el negocio.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base


class Collaborator(Base):
    """
    Modelo de Collaborator para la tabla de colaboradores.
    
    Este modelo almacena información sobre los colaboradores:
    - Nombre del colaborador
    - Email de contacto (opcional)
    - Estado activo/inactivo
    - Timestamps de auditoría
    """
    
    __tablename__ = "collaborators"
    
    # ID único para cada colaborador
    id = Column(Integer, primary_key=True, index=True, comment="Identificador único del colaborador")
    
    # Nombre del colaborador (ej: "Juan Pérez", "María García")
    name = Column(String(100), nullable=False, index=True, comment="Nombre completo del colaborador")
    
    # Email de contacto (opcional, puede ser nulo)
    email = Column(String(255), nullable=True, index=True, comment="Email de contacto del colaborador")
    
    # Control de estado: si el colaborador está activo o no
    is_active = Column(Boolean, default=True, nullable=False, comment="Indica si el colaborador está activo")
    
    # Timestamps automáticos para auditoría
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Fecha de creación")
    
    # Relación uno-a-muchos con appointments
    appointments = relationship("Appointment", back_populates="collaborator", cascade="all, delete-orphan")
    
    def __repr__(self):
        """Representación en string del objeto Collaborator."""
        return f"<Collaborator(id={self.id}, name='{self.name}', email='{self.email}', active={self.is_active})>"
    
    def to_dict(self):
        """Convierte el objeto a un diccionario para fácil serialización."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
