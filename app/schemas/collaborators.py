"""
Esquemas Pydantic para el dominio de colaboradores.
Estos esquemas definen la estructura de datos para validación y serialización.
"""

from typing import Optional, List  # Agregado List para evitar el NameError [cite: 2026-01-30]
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict # Agregado ConfigDict para Pydantic V2 [cite: 2026-02-07]
import re

# Importamos el esquema de horarios para la relación [cite: 2026-02-07]
from app.schemas.business_hours import BusinessHoursRead


class CollaboratorBase(BaseModel):
    """
    Esquema base con los campos comunes para colaboradores.
    """
    name: str = Field(..., min_length=1, max_length=100, description="Nombre completo del colaborador")
    email: Optional[str] = Field(None, max_length=255, description="Email de contacto (opcional)")
    
    # Configuración común para Pydantic V2 [cite: 2026-02-07]
    model_config = ConfigDict(from_attributes=True)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('El nombre del colaborador no puede estar vacío')
        return v.strip()
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v is not None and v.strip():
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v.strip()):
                raise ValueError('El formato del email no es válido')
            return v.strip().lower()
        return v


class CollaboratorCreate(CollaboratorBase):
    """Esquema para creación de colaboradores."""
    pass


class CollaboratorRead(CollaboratorBase):
    """
    Esquema para lectura de colaboradores.
    """
    id: int = Field(..., description="ID único del colaborador")
    is_active: bool = Field(..., description="Indica si el colaborador está activo")
    created_at: datetime = Field(..., description="Fecha de creación")


class CollaboratorUpdate(BaseModel):
    """
    Esquema para actualización parcial de colaboradores.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = Field(None)
    
    model_config = ConfigDict(from_attributes=True) # [cite: 2026-02-07]

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            if not v or not v.strip():
                raise ValueError('El nombre no puede estar vacío')
            return v.strip()
        return v


class CollaboratorWorkSchedule(CollaboratorRead):
    """
    Este esquema envía al frontend el colaborador y sus turnos específicos.
    """
    # Usamos business_hours para coincidir con la relación del modelo [cite: 2026-02-07]
    business_hours: List[BusinessHoursRead] = Field(default=[], description="Lista de horarios del colaborador")