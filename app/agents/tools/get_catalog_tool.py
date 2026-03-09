from typing import List

from sqlalchemy.orm import Session

from app.schemas.services import ServiceRead
from app.services.catalog import get_active_services


def get_catalog_tool(db: Session) -> List[ServiceRead]:
    """
    Tool del agente para obtener el catálogo de servicios activos.
    """
    return get_active_services(db)