from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.agents.schemas.booking import BookingOptionsResponse
from app.services.booking_scheduler import get_booking_options_with_favorites


def get_booking_options_tool(
    db: Session,
    client_phone: str,
    service_id: int,
    target_date: Optional[date] = None
) -> BookingOptionsResponse:
    """
    Tool que obtiene opciones de booking priorizando colaboradores favoritos.
    """

    result = get_booking_options_with_favorites(
        db=db,
        client_phone=client_phone,
        service_id=service_id,
        target_date=target_date
    )

    return BookingOptionsResponse(**result)