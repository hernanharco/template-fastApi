from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.clients import Client


DEFAULT_CLIENT_NAME = "Nuevo Cliente"


def get_client_by_phone(db: Session, phone: str) -> Optional[Client]:
    """
    Busca un cliente por número de teléfono.
    """
    result = db.execute(
        select(Client).where(Client.phone == phone)
    )
    return result.scalar_one_or_none()


def create_client_if_not_exists(db: Session, phone: str) -> Client:
    """
    Crea un cliente si no existe previamente.
    El nombre inicial por defecto será 'Nuevo Cliente'.
    """
    client = get_client_by_phone(db, phone)

    if client:
        return client

    client = Client(
        phone=phone,
        full_name=DEFAULT_CLIENT_NAME,
        metadata_json={}
    )

    db.add(client)
    db.commit()
    db.refresh(client)

    return client


def ensure_client_exists(db: Session, phone: str) -> Client:
    """
    Garantiza que el cliente exista en base de datos.
    Si no existe, lo crea.
    """
    return create_client_if_not_exists(db, phone)


def update_client_name(db: Session, phone: str, new_name: str) -> Optional[Client]:
    """
    Actualiza el nombre del cliente por teléfono.
    Retorna None si el cliente no existe.
    """
    client = get_client_by_phone(db, phone)

    if not client:
        return None

    client.full_name = new_name.strip()

    db.commit()
    db.refresh(client)

    return client


def is_default_client_name(name: Optional[str]) -> bool:
    """
    Indica si el nombre del cliente sigue siendo el nombre por defecto.
    """
    if not name:
        return True

    return name.strip() == DEFAULT_CLIENT_NAME