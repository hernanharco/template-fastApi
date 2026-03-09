# app/agents/tools/find_service_by_text_tool.py

from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.services import Service
from app.services.service_selector import ServiceSelector


def find_service_by_text_tool(
    db: Session,
    user_text: str,
    shown_service_ids: Optional[List[int]] = None,
) -> Optional[Service]:
    """
    Tool para resolver un servicio desde el texto del usuario.
    """

    return ServiceSelector.find_service_by_text(
        db=db,
        user_text=user_text,
        shown_service_ids=shown_service_ids,
    )