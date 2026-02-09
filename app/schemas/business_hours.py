"""
Esquemas Pydantic para el dominio de horarios de negocio.
Estos esquemas definen la estructura de datos para validación y serialización de horarios.
"""

from typing import List, Optional
from datetime import datetime, time
from pydantic import BaseModel, Field, field_validator


class TimeSlotBase(BaseModel):
    """
    Esquema base para slots de tiempo (rangos horarios).
    """
    start_time: str = Field(..., description="Hora de inicio en formato HH:MM")
    end_time: str = Field(..., description="Hora de fin en formato HH:MM")
    slot_order: int = Field(..., ge=1, le=2, description="Orden del slot (1=primero, 2=segundo)")
    
    @field_validator('start_time', 'end_time')
    @classmethod
    def validate_time_format(cls, v):
        """Valida que el formato de hora sea HH:MM."""
        try:
            # Intenta parsear el tiempo para validar el formato
            hour, minute = v.split(':')
            if len(hour) != 2 or len(minute) != 2:
                raise ValueError
            int(hour)  # Valida que sea numérico
            int(minute)
            return v
        except (ValueError, AttributeError):
            raise ValueError('El formato de hora debe ser HH:MM (ej: 09:00)')
    
    @field_validator('end_time')
    @classmethod
    def validate_time_range(cls, v, info):
        """Valida que la hora de fin sea posterior a la de inicio."""
        if 'start_time' in info.data:
            start_hour, start_min = map(int, info.data['start_time'].split(':'))
            end_hour, end_min = map(int, v.split(':'))
            
            start_total = start_hour * 60 + start_min
            end_total = end_hour * 60 + end_min
            
            if end_total <= start_total:
                raise ValueError('La hora de fin debe ser posterior a la hora de inicio')
        return v


class TimeSlotCreate(TimeSlotBase):
    """
    Esquema para creación de slots de tiempo.
    """
    pass


class TimeSlotRead(BaseModel):
    """
    Esquema para lectura de slots de tiempo.
    """
    id: int = Field(..., description="ID único del slot")
    start_time: str = Field(..., description="Hora de inicio en formato HH:MM")
    end_time: str = Field(..., description="Hora de fin en formato HH:MM")
    slot_order: int = Field(..., description="Orden del slot")
    business_hours_id: int = Field(..., description="ID del horario asociado")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")
    
    @classmethod
    def from_orm(cls, obj):
        """Crea instancia desde objeto SQLAlchemy con conversión de time a string."""
        return cls(
            id=obj.id,
            start_time=obj.start_time.strftime("%H:%M") if obj.start_time else None,
            end_time=obj.end_time.strftime("%H:%M") if obj.end_time else None,
            slot_order=obj.slot_order,
            business_hours_id=obj.business_hours_id,
            created_at=obj.created_at,
            updated_at=obj.updated_at
        )


class TimeSlotUpdate(BaseModel):
    """
    Esquema para actualización de slots de tiempo.
    """
    start_time: Optional[str] = Field(None, description="Hora de inicio en formato HH:MM")
    end_time: Optional[str] = Field(None, description="Hora de fin en formato HH:MM")
    slot_order: Optional[int] = Field(None, ge=1, le=2, description="Orden del slot")
    
    @field_validator('start_time', 'end_time')
    @classmethod
    def validate_time_format(cls, v):
        """Valida que el formato de hora sea HH:MM si se proporciona."""
        if v is not None:
            try:
                hour, minute = v.split(':')
                if len(hour) != 2 or len(minute) != 2:
                    raise ValueError
                int(hour)
                int(minute)
                return v
            except (ValueError, AttributeError):
                raise ValueError('El formato de hora debe ser HH:MM (ej: 09:00)')
        return v


class BusinessHoursBase(BaseModel):
    """
    Esquema base para configuración de horarios de negocio.
    """
    day_of_week: int = Field(..., ge=0, le=6, description="Día de la semana (0=Lunes, 6=Domingo)")
    day_name: str = Field(..., min_length=1, max_length=20, description="Nombre del día")
    is_enabled: bool = Field(True, description="Indica si el día está habilitado")
    is_split_shift: bool = Field(False, description="Indica si tiene turno partido")
    
    @field_validator('day_name')
    @classmethod
    def validate_day_name(cls, v):
        """Valida que el nombre del día esté en español y sea válido."""
        valid_days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        if v not in valid_days:
            raise ValueError(f'El nombre del día debe ser uno de: {", ".join(valid_days)}')
        return v
    
    @field_validator('day_of_week')
    @classmethod
    def validate_day_consistency(cls, v, info):
        """Valida que el número de día coincida con el nombre."""
        day_mapping = {
            'Lunes': 0, 'Martes': 1, 'Miércoles': 2, 'Jueves': 3,
            'Viernes': 4, 'Sábado': 5, 'Domingo': 6
        }
        if 'day_name' in info.data and day_mapping.get(info.data['day_name']) != v:
            raise ValueError('El número de día no coincide con el nombre del día')
        return v


class BusinessHoursCreate(BusinessHoursBase):
    """
    Esquema para creación de horarios de negocio.
    Incluye los slots de tiempo asociados.
    """
    time_slots: List[TimeSlotCreate] = Field(..., description="Lista de slots de tiempo para el día")
    
    @field_validator('time_slots')
    @classmethod
    def validate_time_slots(cls, v, info):
        """Valida la consistencia de los slots de tiempo."""
        if not v:
            raise ValueError('Debe proporcionar al menos un slot de tiempo')
        
        # Si no es turno partido, solo debe haber un slot
        if not info.data.get('is_split_shift', False) and len(v) > 1:
            raise ValueError('Si no es turno partido, solo puede haber un slot de tiempo')
        
        # Si es turno partido, debe haber exactamente dos slots
        if info.data.get('is_split_shift', False) and len(v) != 2:
            raise ValueError('Si es turno partido, debe haber exactamente dos slots de tiempo')
        
        # Validar que los slots tengan órdenes correctos
        if len(v) == 2:
            orders = [slot.slot_order for slot in v]
            if sorted(orders) != [1, 2]:
                raise ValueError('Los slots deben tener órdenes 1 y 2 para turno partido')
        
        return v


class BusinessHoursRead(BaseModel):
    """
    Esquema para lectura de horarios de negocio.
    """
    id: int = Field(..., description="ID único del horario")
    day_of_week: int = Field(..., description="Día de la semana (0=Lunes, 6=Domingo)")
    day_name: str = Field(..., description="Nombre del día")
    is_enabled: bool = Field(..., description="Indica si el día está habilitado")
    is_split_shift: bool = Field(..., description="Indica si tiene turno partido")
    time_slots: List[TimeSlotRead] = Field(..., description="Lista de slots de tiempo")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de última actualización")
    
    @classmethod
    def from_orm(cls, obj):
        """Crea instancia desde objeto SQLAlchemy con conversión de time slots."""
        return cls(
            id=obj.id,
            day_of_week=obj.day_of_week,
            day_name=obj.day_name,
            is_enabled=obj.is_enabled,
            is_split_shift=obj.is_split_shift,
            time_slots=[TimeSlotRead.from_orm(slot) for slot in obj.time_slots],
            created_at=obj.created_at,
            updated_at=obj.updated_at
        )


class BusinessHoursUpdate(BaseModel):
    """
    Esquema para actualización de horarios de negocio.
    """
    day_name: Optional[str] = Field(None, min_length=1, max_length=20, description="Nombre del día")
    is_enabled: Optional[bool] = Field(None, description="Indica si el día está habilitado")
    is_split_shift: Optional[bool] = Field(None, description="Indica si tiene turno partido")
    time_slots: Optional[List[TimeSlotCreate]] = Field(None, description="Lista de slots de tiempo")
    
    @field_validator('day_name')
    @classmethod
    def validate_day_name(cls, v):
        """Valida que el nombre del día sea válido si se proporciona."""
        if v is not None:
            valid_days = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            if v not in valid_days:
                raise ValueError(f'El nombre del día debe ser uno de: {", ".join(valid_days)}')
        return v
