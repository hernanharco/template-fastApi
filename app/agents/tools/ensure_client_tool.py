from sqlalchemy.orm import Session

from app.agents.schemas.client import ClientLookupResponse
from app.services.clients import ensure_client_exists, is_default_client_name


def ensure_client_tool(phone: str, db: Session) -> ClientLookupResponse:
    """
    Garantiza que el cliente exista.
    Si no existe, lo crea con el nombre por defecto.
    """
    client = ensure_client_exists(db, phone)

    return ClientLookupResponse(
        exists=True,
        client_name=client.full_name,
        client_id=client.id,
        preferred_collaborators=(client.metadata_json or {}).get(
            "preferred_collaborator_ids", []
        ),
        is_new_user=is_default_client_name(client.full_name)
    )