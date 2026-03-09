from pydantic import BaseModel, Field
from typing import Optional


class GreetingInput(BaseModel):
    client_phone: str = Field(..., description="Teléfono del cliente")
    client_name: Optional[str] = Field(
        default=None,
        description="Nombre del cliente si ya se conoce"
    )
    message: str = Field(..., description="Mensaje recibido del usuario")


class GreetingOutput(BaseModel):
    success: bool = True
    client_name: Optional[str] = None
    requires_name: bool = False
    response_text: str