from pydantic import BaseModel, Field
from typing import List, Optional


class CatalogServiceItem(BaseModel):
    service_id: int
    service_name: str
    duration_minutes: Optional[int] = None
    price: Optional[float] = None
    description: Optional[str] = None


class CatalogInput(BaseModel):
    client_phone: str
    query: Optional[str] = Field(
        default=None,
        description="Texto del usuario para filtrar o consultar servicios"
    )


class CatalogOutput(BaseModel):
    success: bool = True
    services: List[CatalogServiceItem] = []
    response_text: str