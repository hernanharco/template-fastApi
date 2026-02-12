"""
Esquemas Pydantic para el dominio de horarios de negocio.
Actualizado para soportar múltiples colaboradores. [cite: 2026-02-07]
"""

from typing import List, Optional
from datetime import datetime, time
from pydantic import BaseModel, Field, field_validator, ConfigDict, field_serializer


class TimeSlotBase(BaseModel):
    start_time: time = Field(..., description="Hora de inicio")
    end_time: time = Field(..., description="Hora de fin")
    slot_order: int = Field(..., ge=1, le=2, description="Orden del slot (1=primero, 2=segundo)")
    
    model_config = ConfigDict(from_attributes=True) # [cite: 2026-02-07]

class TimeSlotCreate(TimeSlotBase):
    pass

class TimeSlotRead(TimeSlotBase):
    id: int
    business_hours_id: int
    created_at: datetime
    updated_at: datetime
    
    @field_serializer('start_time', 'end_time')
    def serialize_time(self, t: time, _info):
        """Serializa time objects a formato HH:MM string."""
        return t.strftime("%H:%M") if t else None

class BusinessHoursBase(BaseModel):
    """
    Esquema base actualizado con colaborador. [cite: 2026-02-07]
    """
    day_of_week: int = Field(..., ge=0, le=6)
    day_name: str = Field(..., min_length=1, max_length=20)
    is_enabled: bool = True
    is_split_shift: bool = False
    # NUEVO: Permitimos asociar el horario a un colaborador [cite: 2026-02-07]
    collaborator_id: Optional[int] = Field(None, description="ID del colaborador (NULL si es general)")

    model_config = ConfigDict(from_attributes=True) # [cite: 2026-02-07]

    @field_validator('day_name')
    @classmethod
    def validate_day_name(cls, v):
        valid_days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        if v not in valid_days:
            raise ValueError(f'Día inválido: {v}')
        return v

class BusinessHoursCreate(BusinessHoursBase):
    time_slots: List[TimeSlotCreate]

class BusinessHoursRead(BusinessHoursBase):
    id: int
    time_slots: List[TimeSlotRead]
    created_at: datetime
    updated_at: datetime

class BusinessHoursUpdate(BaseModel):
    day_name: Optional[str] = None
    is_enabled: Optional[bool] = None
    is_split_shift: Optional[bool] = None
    collaborator_id: Optional[int] = None # También permitimos actualizarlo
    time_slots: Optional[List[TimeSlotCreate]] = None

class TimeSlotUpdate(BaseModel):
    """
    Esquema para actualización de slots de tiempo.
    Todos los campos son opcionales para permitir actualizaciones parciales. [cite: 2026-02-07]
    """
    start_time: Optional[time] = Field(None, description="Hora de inicio")
    end_time: Optional[time] = Field(None, description="Hora de fin")
    slot_order: Optional[int] = Field(None, ge=1, le=2, description="Orden del slot")
    
    model_config = ConfigDict(from_attributes=True) # [cite: 2026-02-07]

    @field_serializer('start_time', 'end_time')
    def serialize_time(self, t: time, _info):
        return t.strftime("%H:%M") if t else None