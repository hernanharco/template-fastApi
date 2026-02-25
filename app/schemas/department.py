from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional

class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None
    # 🎨 Añadimos el color con un valor por defecto (Azul Tailwind por defecto)
    color: str = Field(default="#3B82F6", pattern="^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$")
    is_active: bool = True

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(BaseModel):
    # En el update, todos los campos deben ser opcionales para permitir cambios parciales
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = Field(None, pattern="^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$")
    is_active: Optional[bool] = None

class Department(DepartmentBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)