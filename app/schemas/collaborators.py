from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re

class CollaboratorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    model_config = ConfigDict(from_attributes=True)

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v and v.strip():
            return v.strip().lower()
        return v

class CollaboratorCreate(CollaboratorBase):
    # Recibimos los IDs del frontend
    department_ids: List[int] = Field(default=[])

class CollaboratorRead(CollaboratorBase):
    id: int
    is_active: bool
    created_at: datetime
    # Usamos alias para decirle a Pydantic: 
    # "Busca en el atributo 'departments' de la base de datos"
    department_ids: List[int] = Field(default=[], alias="departments")

    @field_validator("department_ids", mode="before")
    @classmethod
    def extract_ids(cls, v):
        # SQLAlchemy entrega una lista de objetos Department
        # Este bloque los convierte en [1, 2, 3]
        if isinstance(v, list) and v and hasattr(v[0], 'id'):
            return [dept.id for dept in v]
        return v

    # populate_by_name es clave para que el JSON final diga "department_ids"
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class CollaboratorUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    department_ids: Optional[List[int]] = None
    model_config = ConfigDict(from_attributes=True)