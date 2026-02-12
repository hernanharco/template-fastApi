from pydantic import BaseModel, EmailStr
from typing import Optional, Any, Dict

class ClientBase(BaseModel):
    full_name: str
    phone: str
    email: Optional[EmailStr] = None
    metadata_json: Optional[Dict[str, Any]] = {}

class ClientCreate(ClientBase):
    pass  # Lo que usamos para crear un cliente nuevo

class ClientResponse(ClientBase):
    id: int
    # Esto permite que Pydantic lea los datos directamente de SQLAlchemy
    class Config:
        from_attributes = True