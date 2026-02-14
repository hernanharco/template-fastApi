from typing import TypedDict, Optional

class BookingState(TypedDict):
    messages: list
    service_type: str
    service_id: Optional[int]
    appointment_date: Optional[str]
    appointment_time: Optional[str]
    available_slots: Optional[str]
    current_date: str