from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AppointmentData(BaseModel):
    appointment_id: Optional[int] = None
    client_phone: str
    service_id: int
    collaborator_id: int
    scheduled_at: datetime
    status: str


class AppointmentConfirmationOutput(BaseModel):
    success: bool
    appointment: Optional[AppointmentData] = None
    response_text: str