# app/schemas/booking.py

from typing import List, Optional
from pydantic import BaseModel, Field


class BookingOption(BaseModel):
    option_number: int
    time: str
    full_datetime: str
    collaborator_id: int
    is_favorite: bool = False
    duration_minutes: Optional[int] = None


class BookingOptionsResponse(BaseModel):
    success: bool
    service: Optional[str] = None
    service_id: Optional[int] = None
    date: Optional[str] = None
    client: Optional[str] = None
    has_favorites: bool = False
    options: List[BookingOption] = Field(default_factory=list)
    selection_prompt: Optional[str] = None
    message: Optional[str] = None
    suggestions: List[str] = Field(default_factory=list)


class SlotValidationResponse(BaseModel):
    valid: bool
    reason: str