from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.services import Service
from app.schemas.services import ServiceRead


def get_active_services(db: Session) -> List[ServiceRead]:
    """
    Obtiene todos los servicios activos del catálogo.
    """
    result = db.execute(
        select(Service)
        .options(selectinload(Service.department))
        .where(Service.is_active == True)
        .order_by(Service.name.asc())
    )

    services = result.scalars().all()

    return [ServiceRead.model_validate(service) for service in services]