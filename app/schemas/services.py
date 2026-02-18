"""
Esquemas Pydantic para el dominio de servicios.
Define la validación y serialización de datos para el catálogo de servicios.
Basado en el principio: "Menos infraestructura, más valor".
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict

class ServiceBase(BaseModel):
    """
    Campos base compartidos. 
    Incluye department_id ya que un servicio debe pertenecer a un área.
    """
    name: str = Field(..., min_length=1, max_length=100, description="Nombre del servicio")
    duration_minutes: int = Field(..., gt=0, le=480, description="Duración en minutos (múltiplos de 5)")
    price: float = Field(..., gt=0, description="Precio (máximo 2 decimales)")
    department_id: int = Field(..., description="ID del departamento responsable")
    
    # Configuración Pydantic V2 para leer modelos de SQLAlchemy
    model_config = ConfigDict(from_attributes=True)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('El nombre del servicio no puede estar vacío')
        return v.strip()
    
    @field_validator('duration_minutes')
    @classmethod
    def validate_duration(cls, v):
        if v % 5 != 0:
            raise ValueError('La duración debe ser en múltiplos de 5 minutos para la agenda')
        return v
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v):
        if round(v, 2) != v:
            raise ValueError('El precio puede tener máximo 2 decimales')
        return v

class ServiceCreate(ServiceBase):
    """Esquema para la creación de nuevos servicios."""
    pass

class ServiceRead(ServiceBase):
    """
    Esquema para la lectura de datos. 
    Incluye campos automáticos de la base de datos.
    """
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

class ServiceUpdate(BaseModel):
    """
    Esquema para actualización. Todos los campos son opcionales.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    duration_minutes: Optional[int] = Field(None, gt=0, le=480)
    price: Optional[float] = Field(None, gt=0)
    department_id: Optional[int] = None
    is_active: Optional[bool] = None
    
    model_config = ConfigDict(from_attributes=True)

    @field_validator('duration_minutes')
    @classmethod
    def validate_duration(cls, v):
        if v is not None and v % 5 != 0:
            raise ValueError('La duración debe ser en múltiplos de 5 minutos')
        return v
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v):
        if v is not None and round(v, 2) != v:
            raise ValueError('El precio puede tener máximo 2 decimales')
        return v