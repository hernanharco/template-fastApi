"""
Esquemas Pydantic para el dominio de colaboradores.
Estos esquemas definen la estructura de datos para validación y serialización.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import re


class CollaboratorBase(BaseModel):
    """
    Esquema base con los campos comunes para colaboradores.
    Contiene los campos que se comparten entre creación y actualización.
    """
    name: str = Field(..., min_length=1, max_length=100, description="Nombre completo del colaborador")
    email: Optional[str] = Field(None, max_length=255, description="Email de contacto (opcional)")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Valida que el nombre no esté vacío y elimina espacios extras."""
        if not v or not v.strip():
            raise ValueError('El nombre del colaborador no puede estar vacío')
        return v.strip()
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Valida el formato del email si se proporciona."""
        if v is not None and v.strip():
            # Expresión regular básica para validar email
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v.strip()):
                raise ValueError('El formato del email no es válido')
            return v.strip().lower()  # Normalizar a minúsculas
        return v


class CollaboratorCreate(CollaboratorBase):
    """
    Esquema para creación de colaboradores.
    Hereda todos los campos del base sin modificaciones.
    """
    pass


class CollaboratorRead(BaseModel):
    """
    Esquema para lectura de colaboradores.
    Contiene todos los campos que se devolverán en las respuestas de la API.
    """
    id: int = Field(..., description="ID único del colaborador")
    name: str = Field(..., description="Nombre completo del colaborador")
    email: Optional[str] = Field(None, description="Email de contacto")
    is_active: bool = Field(..., description="Indica si el colaborador está activo")
    created_at: datetime = Field(..., description="Fecha de creación")
    
    class Config:
        """Configuración para permitir la creación desde objetos ORM."""
        from_attributes = True


class CollaboratorUpdate(BaseModel):
    """
    Esquema para actualización de colaboradores.
    Todos los campos son opcionales para permitir actualizaciones parciales.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Nombre completo del colaborador")
    email: Optional[str] = Field(None, max_length=255, description="Email de contacto")
    is_active: Optional[bool] = Field(None, description="Estado activo/inactivo del colaborador")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        """Valida el nombre si se proporciona."""
        if v is not None:
            if not v or not v.strip():
                raise ValueError('El nombre del colaborador no puede estar vacío')
            return v.strip()
        return v
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """Valida el email si se proporciona."""
        if v is not None and v.strip():
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, v.strip()):
                raise ValueError('El formato del email no es válido')
            return v.strip().lower()
        return v
