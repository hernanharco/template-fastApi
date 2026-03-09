from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.schemas.booking import BookingOption
from app.services.availability import get_available_slots


def get_available_slots_tool(
    service_id: int,
    target_date: datetime,
    db: Session
) -> List[BookingOption]:
    """
    Tool para obtener slots disponibles para un servicio.
    """

    slots = get_available_slots(
        db=db,
        target_date=target_date,
        service_id=service_id
    )

    return [
        BookingOption(
            start_time=slot["start_time"],
            end_time=slot["end_time"],
            collaborator_id=slot["collaborator_id"],
            collaborator_name=slot["collaborator_name"]
        )
        for slot in slots
    ]