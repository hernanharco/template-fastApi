import json
from sqlalchemy.orm import Session

from app.agents.schemas.client import ClientLookupResponse
from app.services.clients import ensure_client_exists, is_default_client_name


def _parse_preferred_collaborators(metadata_json) -> list:
    """
    Extrae preferred_collaborator_ids de metadata_json de forma segura.
    Maneja tanto dict como string JSON, igual que _get_favorites() en el scheduler.
    """
    if not metadata_json:
        return []

    if isinstance(metadata_json, str):
        try:
            metadata_json = json.loads(metadata_json)
        except (json.JSONDecodeError, TypeError):
            return []

    if isinstance(metadata_json, dict):
        # Soporta {"preferred_collaborator_ids": [...]}
        if "preferred_collaborator_ids" in metadata_json:
            return metadata_json["preferred_collaborator_ids"]
        # Soporta {"profile": {"preferred_collaborator_ids": [...]}}
        if "profile" in metadata_json and isinstance(metadata_json["profile"], dict):
            return metadata_json["profile"].get("preferred_collaborator_ids", [])

    return []


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
        preferred_collaborators=_parse_preferred_collaborators(client.metadata_json),
        is_new_user=is_default_client_name(client.full_name),
    )