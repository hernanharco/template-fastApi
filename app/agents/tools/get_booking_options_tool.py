from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.agents.schemas.booking import BookingOptionsResponse
from app.services.booking_scheduler import get_booking_options_with_favorites


def get_booking_options_tool(
    db: Session,
    client_phone: str,
    service_id: int,
    target_date: Optional[date] = None,
    min_hour: Optional[int] = None,   # filtro "después de las X"
    max_hour: Optional[int] = None,   # filtro "antes de las X"
    limit: Optional[int] = 2,         # None = sin límite (para first/last)
) -> BookingOptionsResponse:
    """
    Tool que obtiene opciones de booking priorizando colaboradores favoritos.
    Acepta filtros horarios opcionales para buscar slots en un rango específico.
    Usar limit=None para first/last ya que necesitamos todos los slots del día.
    """

    result = get_booking_options_with_favorites(
        db=db,
        client_phone=client_phone,
        service_id=service_id,
        target_date=target_date,
        min_hour=min_hour,
        max_hour=max_hour,
        limit=limit,
    )

    return BookingOptionsResponse(**result)