"""
Esquemas Pydantic para el dominio de servicios.
Estos esquemas definen la estructura de datos para validación y serialización.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class ServiceBase(BaseModel):
    """
    Esquema base con los campos comunes para servicios.
    Contiene los campos que se comparten entre creación y actualización.
    """
    name: str = Field(..., min_length=1, max_length=100, description="Nombre del servicio")
    duration_minutes: int = Field(..., gt=0, le=480, description="Duración en minutos (máximo 8 horas)")
    price: float = Field(..., gt=0, description="Precio del servicio (debe ser mayor a 0)")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Valida que el nombre no esté vacío y elimina espacios extras."""
        if not v or not v.strip():
            raise ValueError('El nombre del servicio no puede estar vacío')
        return v.strip()
    
    @field_validator('duration_minutes')
    @classmethod
    def validate_duration(cls, v):
        """Valida que la duración sea un múltiplo de 5 minutos."""
        if v % 5 != 0:
            raise ValueError('La duración debe ser en múltiplos de 5 minutos')
        return v
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v):
        """Valida que el precio tenga máximo 2 decimales."""
        if round(v, 2) != v:
            raise ValueError('El precio puede tener máximo 2 decimales')
        return v


class ServiceCreate(ServiceBase):
    """
    Esquema para creación de servicios.
    Hereda todos los campos del base sin modificaciones.
    """
    pass


class ServiceRead(BaseModel):
    """
    Esquema para lectura de servicios.
    Contiene todos los campos que se devolverán en las respuestas de la API.
    """
    id: int = Field(..., description="ID único del servicio")
    name: str = Field(..., description="Nombre del servicio")
    duration_minutes: int = Field(..., description="Duración en minutos")
    price: float = Field(..., description="Precio del servicio")
    is_active: bool = Field(..., description="Indica si el servicio está activo")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")
    
    class Config:
        """Configuración para permitir la creación desde objetos ORM."""
        from_attributes = True


class ServiceUpdate(BaseModel):
    """
    Esquema para actualización de servicios.
    Todos los campos son opcionales para permitir actualizaciones parciales.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Nombre del servicio")
    duration_minutes: Optional[int] = Field(None, gt=0, le=480, description="Duración en minutos")
    price: Optional[float] = Field(None, gt=0, description="Precio del servicio")
    is_active: Optional[bool] = Field(None, description="Estado activo/inactivo del servicio")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Valida el nombre si se proporciona."""
        if v is not None:
            if not v or not v.strip():
                raise ValueError('El nombre del servicio no puede estar vacío')
            return v.strip()
        return v
    
    @field_validator('duration_minutes')
    @classmethod
    def validate_duration(cls, v):
        """Valida la duración si se proporciona."""
        if v is not None and v % 5 != 0:
            raise ValueError('La duración debe ser en múltiplos de 5 minutos')
        return v
    
    @field_validator('price')
    @classmethod
    def validate_price(cls, v):
        """Valida el precio si se proporciona."""
        if v is not None and round(v, 2) != v:
            raise ValueError('El precio puede tener máximo 2 decimales')
        return v
