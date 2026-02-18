from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

class ClientBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=5, max_length=20)
    email: Optional[str] = None
    notes: Optional[str] = None
    source: str = Field(default="manual") 
    is_active: bool = True

class ClientCreate(ClientBase):
    business_id: Optional[int] = 1

class ClientUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    source: Optional[str] = None

class ClientResponse(ClientBase): 
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Esto permite que Pydantic lea los modelos de SQLAlchemy (Neon)
    model_config = ConfigDict(from_attributes=True)