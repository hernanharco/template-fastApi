"""
Esquemas Pydantic para el dominio de citas.
Estos esquemas definen la estructura de datos para validación y serialización.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from app.models.appointments import AppointmentStatus


class AppointmentBase(BaseModel):
    """
    Esquema base con los campos comunes para citas.
    Contiene los campos que se comparten entre creación y actualización.
    """
    service_id: int = Field(..., gt=0, description="ID del servicio solicitado")
    collaborator_id: int = Field(..., gt=0, description="ID del colaborador asignado")
    client_name: str = Field(..., min_length=1, max_length=100, description="Nombre completo del cliente")
    client_phone: Optional[str] = Field(None, max_length=20, description="Teléfono de contacto del cliente")
    client_email: Optional[str] = Field(None, max_length=255, description="Email del cliente")
    client_notes: Optional[str] = Field(None, max_length=1000, description="Notas adicionales del cliente")
    start_time: datetime = Field(..., description="Fecha y hora de inicio de la cita")
    end_time: datetime = Field(..., description="Fecha y hora de fin de la cita")
    
    @field_validator('client_name')
    @classmethod
    def validate_client_name(cls, v):
        """Valida que el nombre del cliente no esté vacío."""
        if not v or not v.strip():
            raise ValueError('El nombre del cliente no puede estar vacío')
        return v.strip()
    
    @field_validator('client_phone')
    @classmethod
    def validate_phone(cls, v):
        """Valida el formato del teléfono si se proporciona."""
        if v is not None and v.strip():
            # Eliminamos espacios y caracteres no numéricos excepto +
            phone = ''.join(c for c in v.strip() if c.isdigit() or c == '+')
            if len(phone) < 8:
                raise ValueError('El teléfono debe tener al menos 8 dígitos')
            return phone
        return v
    
    @field_validator('client_email')
    @classmethod
    def validate_email(cls, v):
        """Valida el formato del email si se proporciona."""
        if v is not None and v.strip():
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not email_pattern.match(v.strip()):
                raise ValueError('El formato del email no es válido')
            return v.strip().lower()
        return v
    
    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v, info):
        """Valida que la hora de fin sea posterior a la de inicio."""
        if 'start_time' in info.data:
            start_time = info.data['start_time']
            if v <= start_time:
                raise ValueError('La hora de fin debe ser posterior a la hora de inicio')
        return v


class AppointmentCreate(AppointmentBase):
    """
    Esquema para creación de citas.
    Hereda todos los campos del base sin modificaciones.
    """
    pass


class AppointmentRead(BaseModel):
    """
    Esquema para lectura de citas.
    Contiene todos los campos que se devolverán en las respuestas de la API.
    """
    id: int = Field(..., description="ID único de la cita")
    service_id: int = Field(..., description="ID del servicio")
    collaborator_id: int = Field(..., description="ID del colaborador")
    client_name: str = Field(..., description="Nombre del cliente")
    client_phone: Optional[str] = Field(None, description="Teléfono del cliente")
    client_email: Optional[str] = Field(None, description="Email del cliente")
    client_notes: Optional[str] = Field(None, description="Notas del cliente")
    start_time: datetime = Field(..., description="Fecha y hora de inicio")
    end_time: datetime = Field(..., description="Fecha y hora de fin")
    status: AppointmentStatus = Field(..., description="Estado de la cita")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")
    
    # Campos calculados
    duration_minutes: Optional[int] = Field(None, description="Duración en minutos")
    is_active: bool = Field(..., description="Indica si la cita está activa")
    
    class Config:
        """Configuración para permitir la creación desde objetos ORM."""
        from_attributes = True


class AppointmentUpdate(BaseModel):
    """
    Esquema para actualización de citas.
    Todos los campos son opcionales para permitir actualizaciones parciales.
    """
    service_id: Optional[int] = Field(None, gt=0, description="ID del servicio")
    collaborator_id: Optional[int] = Field(None, gt=0, description="ID del colaborador")
    client_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Nombre del cliente")
    client_phone: Optional[str] = Field(None, max_length=20, description="Teléfono del cliente")
    client_email: Optional[str] = Field(None, max_length=255, description="Email del cliente")
    client_notes: Optional[str] = Field(None, max_length=1000, description="Notas del cliente")
    start_time: Optional[datetime] = Field(None, description="Fecha y hora de inicio")
    end_time: Optional[datetime] = Field(None, description="Fecha y hora de fin")
    status: Optional[AppointmentStatus] = Field(None, description="Estado de la cita")
    
    @field_validator('client_name')
    @classmethod
    def validate_client_name(cls, v):
        """Valida el nombre del cliente si se proporciona."""
        if v is not None:
            if not v or not v.strip():
                raise ValueError('El nombre del cliente no puede estar vacío')
            return v.strip()
        return v
    
    @field_validator('client_phone')
    @classmethod
    def validate_phone(cls, v):
        """Valida el teléfono si se proporciona."""
        if v is not None and v.strip():
            phone = ''.join(c for c in v.strip() if c.isdigit() or c == '+')
            if len(phone) < 8:
                raise ValueError('El teléfono debe tener al menos 8 dígitos')
            return phone
        return v
    
    @field_validator('client_email')
    @classmethod
    def validate_email(cls, v):
        """Valida el email si se proporciona."""
        if v is not None and v.strip():
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not email_pattern.match(v.strip()):
                raise ValueError('El formato del email no es válido')
            return v.strip().lower()
        return v


class TimeSlot(BaseModel):
    """
    Esquema para representar un hueco libre disponible.
    """
    start_time: datetime = Field(..., description="Hora de inicio del hueco")
    end_time: datetime = Field(..., description="Hora de fin del hueco")
    collaborator_id: int = Field(..., description="ID del colaborador disponible")
    collaborator_name: str = Field(..., description="Nombre del colaborador")
    available_minutes: int = Field(..., description="Minutos disponibles en este hueco")


class AvailableSlotsResponse(BaseModel):
    """
    Esquema para la respuesta de huecos disponibles.
    """
    date: str = Field(..., description="Fecha consultada (YYYY-MM-DD)")
    service_id: int = Field(..., description="ID del servicio consultado")
    service_duration: int = Field(..., description="Duración del servicio en minutos")
    available_slots: list[TimeSlot] = Field(..., description="Lista de huecos disponibles")
    total_slots: int = Field(..., description="Número total de huecos disponibles")
