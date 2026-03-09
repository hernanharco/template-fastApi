from sqlalchemy.orm import Session
from datetime import datetime

from app.services.availability import is_valid_appointment_time
from app.schemas.booking import SlotValidationResponse


def validate_slot_tool(
    collaborator_id: int,
    start_time: datetime,
    end_time: datetime,
    db: Session
) -> SlotValidationResponse:

    valid, reason = is_valid_appointment_time(
        db=db,
        collaborator_id=collaborator_id,
        start_time=start_time,
        end_time=end_time
    )

    return SlotValidationResponse(
        valid=valid,
        reason=reason
    )