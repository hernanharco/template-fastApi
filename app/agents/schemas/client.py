from typing import Optional, List

from pydantic import BaseModel, Field


class ClientLookupResponse(BaseModel):
    exists: bool
    client_name: Optional[str] = None
    client_id: Optional[int] = None
    preferred_collaborators: List[int] = Field(default_factory=list)
    is_new_user: bool = False