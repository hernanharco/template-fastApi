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
    - Relación con sus horarios de trabajo y citas
    """
    
    __tablename__ = "collaborators"
    
    # ID único para cada colaborador
    id = Column(Integer, primary_key=True, index=True, comment="Identificador único del colaborador")
    
    # Nombre del colaborador
    name = Column(String(100), nullable=False, index=True, comment="Nombre completo del colaborador")
    
    # Email de contacto
    email = Column(String(255), nullable=True, index=True, comment="Email de contacto del colaborador")
    
    # Control de estado: permite desactivar un colaborador sin borrar su historial
    is_active = Column(Boolean, default=True, nullable=False, comment="Indica si el colaborador está activo")
    
    # Timestamps automáticos para auditoría
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Fecha de creación")
    
    # --- RELACIONES --- [cite: 2026-02-07]

    # 1. Relación con BusinessHours (Nueva):
    # Permite ver los días y horas que trabaja este colaborador específico.
    # cascade="all, delete-orphan" asegura que si borras al colaborador, se limpian sus horarios.
    business_hours = relationship(
        "BusinessHours", 
        back_populates="collaborator", 
        cascade="all, delete-orphan"
    )
    
    # 2. Relación con Appointments:
    # Mantiene el vínculo con las citas que tiene asignadas.
    appointments = relationship(
        "Appointment", 
        back_populates="collaborator", 
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        """Representación en string del objeto Collaborator."""
        return f"<Collaborator(id={self.id}, name='{self.name}', active={self.is_active})>"
    
    def to_dict(self):
        """Convierte el objeto a un diccionario incluyendo la información básica."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }