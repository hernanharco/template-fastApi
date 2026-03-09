from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.services.availability import find_available_collaborator


def find_collaborator_tool(
    service_id: int,
    start_time: datetime,
    end_time: datetime,
    db: Session,
    collaborator_id: Optional[int] = None
) -> Optional[int]:
    """
    Busca un colaborador disponible.
    """

    return find_available_collaborator(
        db=db,
        start_time=start_time,
        end_time=end_time,
        service_id=service_id,
        collaborator_id=collaborator_id
    )