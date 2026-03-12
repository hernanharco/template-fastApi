import json
from sqlalchemy.orm import Session

from app.agents.schemas.client import ClientLookupResponse
from app.services.clients import update_client_name, is_default_client_name


def _parse_preferred_collaborators(metadata_json) -> list:
    if not metadata_json:
        return []
    if isinstance(metadata_json, str):
        try:
            metadata_json = json.loads(metadata_json)
        except (json.JSONDecodeError, TypeError):
            return []
    if isinstance(metadata_json, dict):
        if "preferred_collaborator_ids" in metadata_json:
            return metadata_json["preferred_collaborator_ids"]
        if "profile" in metadata_json and isinstance(metadata_json["profile"], dict):
            return metadata_json["profile"].get("preferred_collaborator_ids", [])
    return []


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
            is_new_user=False,
        )

    return ClientLookupResponse(
        exists=True,
        client_name=client.full_name,
        client_id=client.id,
        preferred_collaborators=_parse_preferred_collaborators(client.metadata_json),
        is_new_user=is_default_client_name(client.full_name),
    )