from datetime import datetime

from sqlalchemy.orm import Session

from app.schemas.booking import SlotValidationResponse
from app.services.availability import is_valid_appointment_time


def validate_slot_tool(
    collaborator_id: int,
    start_time: datetime,
    end_time: datetime,
    db: Session
) -> SlotValidationResponse:
    """
    Valida si un horario sigue disponible para una cita.
    """

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