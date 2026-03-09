from sqlalchemy.orm import Session

from app.agents.schemas.client import ClientLookupResponse
from app.services.clients import update_client_name, is_default_client_name


def update_client_name_tool(
    phone: str,
    new_name: str,
    db: Session
) -> ClientLookupResponse:
    """
    Actualiza el nombre del cliente y devuelve el estado actualizado.
    """
    client = update_client_name(db, phone, new_name)

    if not client:
        return ClientLookupResponse(
            exists=False,
            client_name=None,
            client_id=None,
            preferred_collaborators=[],
            is_new_user=False
        )

    return ClientLookupResponse(
        exists=True,
        client_name=client.full_name,
        client_id=client.id,
        preferred_collaborators=(client.metadata_json or {}).get(
            "preferred_collaborator_ids", []
        ),
        is_new_user=is_default_client_name(client.full_name)
    )