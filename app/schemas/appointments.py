import re
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ValidationInfo, ConfigDict, computed_field
from app.models.appointments import AppointmentStatus

class AppointmentBase(BaseModel):
    service_id: int = Field(..., gt=0)
    collaborator_id: Optional[int] = Field(None, gt=0)
    client_name: str = Field(..., min_length=1, max_length=100)
    client_phone: Optional[str] = Field(None, max_length=20)
    client_email: Optional[str] = Field(None, max_length=255)
    client_notes: Optional[str] = Field(None, max_length=1000)
    start_time: datetime
    end_time: datetime
    
    @field_validator('start_time', 'end_time', mode='before')
    @classmethod
    def clean_tz_info(cls, v):
        if isinstance(v, str):
            # Si viene como string, lo convertimos a datetime primero
            v = datetime.fromisoformat(v.replace('Z', '+00:00'))
        if isinstance(v, datetime):
            return v.replace(tzinfo=None)
        return v

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentRead(BaseModel):
    # Campos que existen en la base de datos
    id: int
    client_id: Optional[int] = None
    service_id: int
    collaborator_id: Optional[int] = None
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
    
    # --- PROPIEDAD CALCULADA ---
    # Usamos computed_field para que Pydantic lea la @property del modelo
    @computed_field
    @property
    def is_active(self) -> bool:
        # Esta lógica debe coincidir con la de tu modelo
        return self.status in [AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED]

    # Configuración para Pydantic v2
    model_config = ConfigDict(from_attributes=True)

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

    @field_validator('start_time', 'end_time')
    @classmethod
    def clean_update_times(cls, v: Optional[datetime]):
        if v is None: return v
        return v.replace(tzinfo=None) if v.tzinfo else v

# --- Otros esquemas ---
class TimeSlot(BaseModel):
    start_time: datetime
    end_time: datetime
    collaborator_id: int
    collaborator_name: str
    available_minutes: int

class AvailableSlotsResponse(BaseModel):
    date: str
    service_id: int
    service_duration: int
    available_slots: List[TimeSlot]
    total_slots: int