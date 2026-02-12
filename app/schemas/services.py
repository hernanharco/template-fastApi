"""
Esquemas Pydantic para el dominio de servicios.
Estos esquemas definen la estructura de datos para validación y serialización.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict # [cite: 2026-02-07]


class ServiceBase(BaseModel):
    """
    Esquema base con los campos comunes para servicios.
    """
    name: str = Field(..., min_length=1, max_length=100, description="Nombre del servicio")
    duration_minutes: int = Field(..., gt=0, le=480, description="Duración en minutos (máximo 8 horas)")
    price: float = Field(..., gt=0, description="Precio del servicio (debe ser mayor a 0)")
    
    # NUEVO: Configuración para Pydantic V2 [cite: 2026-02-07]
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
            raise ValueError('La duración debe ser en múltiplos de 5 minutos')
        return v
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v):
        if round(v, 2) != v:
            raise ValueError('El precio puede tener máximo 2 decimales')
        return v


class ServiceCreate(ServiceBase):
    """Esquema para creación de servicios."""
    pass


class ServiceRead(ServiceBase): # Heredamos de ServiceBase para no repetir campos [cite: 2026-01-30]
    """
    Esquema para lectura de servicios.
    """
    id: int = Field(..., description="ID único del servicio")
    is_active: bool = Field(..., description="Indica si el servicio está activo")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")


class ServiceUpdate(BaseModel):
    """
    Esquema para actualización de servicios.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    duration_minutes: Optional[int] = Field(None, gt=0, le=480)
    price: Optional[float] = Field(None, gt=0)
    is_active: Optional[bool] = Field(None)
    
    model_config = ConfigDict(from_attributes=True) # [cite: 2026-02-07]

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if v is not None:
            if not v or not v.strip():
                raise ValueError('El nombre del servicio no puede estar vacío')
            return v.strip()
        return v
    
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