from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class DepartmentBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True

class DepartmentCreate(DepartmentBase):
    pass

class DepartmentUpdate(DepartmentBase):
    name: Optional[str] = None

class Department(DepartmentBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)