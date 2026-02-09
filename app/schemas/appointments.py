import re
import pytz
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ValidationInfo, field_serializer
from app.models.appointments import AppointmentStatus
from app.core.settings import settings  # Corregido a .settings según tu main.py

# Configuración de zona horaria desde el .env
BUSINESS_TZ = pytz.timezone(settings.APP_TIMEZONE)

class AppointmentBase(BaseModel):
    service_id: int = Field(..., gt=0)
    collaborator_id: int = Field(..., gt=0)
    client_name: str = Field(..., min_length=1, max_length=100)
    client_phone: Optional[str] = Field(None, max_length=20)
    client_email: Optional[str] = Field(None, max_length=255)
    client_notes: Optional[str] = Field(None, max_length=1000)
    start_time: datetime
    end_time: datetime
    
    @field_validator('start_time')
    @classmethod
    def validate_start_time(cls, v: datetime):
        # 1. Obtenemos la hora actual en la zona del negocio (España)
        now_business = datetime.now(BUSINESS_TZ)
        
        # 2. Convertimos la hora que llega (v) a la zona del negocio
        # Si viene con 'Z' (UTC), astimezone lo mueve a +01:00 correctamente
        v_localized = v.astimezone(BUSINESS_TZ) if v.tzinfo else BUSINESS_TZ.localize(v)
        
        # 3. Debug para que veas en la terminal qué está pasando realmente
        print(f"DEBUG: Cita recibida: {v} | Localizada: {v_localized} | Ahora en negocio: {now_business}")

        if v_localized < now_business:
            raise ValueError("No se pueden programar citas en el pasado")
            
        return v_localized

    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v: datetime, info: ValidationInfo):
        if 'start_time' in info.data:
            start_time = info.data['start_time']
            v_localized = v.astimezone(BUSINESS_TZ) if v.tzinfo else BUSINESS_TZ.localize(v)
            if v_localized <= start_time:
                raise ValueError('La hora de fin debe ser posterior a la hora de inicio')
        return v

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentRead(BaseModel):
    id: int
    service_id: int
    collaborator_id: int
    client_name: str
    client_phone: Optional[str] = None
    client_email: Optional[str] = None
    client_notes: Optional[str] = None
    start_time: datetime
    end_time: datetime
    status: AppointmentStatus
    created_at: datetime
    updated_at: datetime
    duration_minutes: Optional[int] = None
    is_active: bool

    # Formateamos TODAS las fechas que salen al Frontend
    @field_serializer('start_time', 'end_time', 'created_at', 'updated_at')
    def serialize_dt(self, dt: datetime, _info):
        if dt is None:
            return None
        # Convertimos de UTC a la hora de España/Negocio para el JSON de salida
        return dt.astimezone(BUSINESS_TZ).isoformat()
    
    class Config:
        from_attributes = True

class AppointmentUpdate(BaseModel):
    service_id: Optional[int] = None
    collaborator_id: Optional[int] = None
    client_name: Optional[str] = None
    client_phone: Optional[str] = None
    client_email: Optional[str] = None
    client_notes: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: Optional[AppointmentStatus] = None

# --- ESTAS SON LAS CLASES QUE FALTABAN ---
class TimeSlot(BaseModel):
    """Esquema para representar un hueco libre disponible."""
    start_time: datetime
    end_time: datetime
    collaborator_id: int
    collaborator_name: str
    available_minutes: int

    # También formateamos los huecos libres para que el calendario de Svelte los vea bien
    @field_serializer('start_time', 'end_time')
    def serialize_dt(self, dt: datetime, _info):
        return dt.astimezone(BUSINESS_TZ).isoformat()

class AvailableSlotsResponse(BaseModel):
    """Esquema para la respuesta de huecos disponibles."""
    date: str
    service_id: int
    service_duration: int
    available_slots: List[TimeSlot]
    total_slots: int