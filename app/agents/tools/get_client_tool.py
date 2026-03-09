from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.clients import Client
from app.agents.schemas.client import ClientLookupResponse


def get_client_tool(phone: str, db: Session) -> ClientLookupResponse:
    """
    Obtiene un cliente por teléfono.
    """

    result = db.execute(
        select(Client).where(Client.phone == phone)
    )

    client = result.scalar_one_or_none()

    if not client:
        return ClientLookupResponse(
            exists=False,
            client_name=None,
            client_id=None,
            preferred_collaborators=[]
        )

    return ClientLookupResponse(
        exists=True,
        client_name=client.full_name,
        client_id=client.id,
        preferred_collaborators=(client.metadata_json or {}).get(
            "preferred_collaborator_ids", []
        )
    )