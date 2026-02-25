# app/schemas/reminder.py
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class ReminderBase(BaseModel):
    appointment_id: int
    message: str
    scheduled_for: datetime
    prefer_channel: str = "telegram"

class ReminderCreate(ReminderBase):
    phone: Optional[str] = None
    telegram_chat_id: Optional[str] = None

class ReminderRead(ReminderBase):
    id: int
    sent: bool
    sent_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)