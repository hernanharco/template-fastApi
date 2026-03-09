#app.schemas.client.py
from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional, Dict, Any, List
from datetime import datetime

class ClientBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=100)
    # Prioridad absoluta: El celular (mínimo 9 dígitos para ser real)
    phone: str = Field(..., min_length=9, max_length=20)
    # Email como texto simple y opcional (sin validación estricta)
    email: Optional[str] = None
    notes: Optional[str] = None
    source: str = Field(default="ia")
    is_active: bool = True
    
    # 🧠 ESTADO DE LA SESIÓN (Singular: Lo que está eligiendo AHORA con la IA)
    current_service_id: Optional[int] = Field(None, description="ID del servicio en proceso de reserva")
    current_collaborator_id: Optional[int] = Field(None, description="ID del colaborador seleccionado para esta cita")

    # ⭐ PREFERENCIAS (Plural: Los que el usuario seleccionó en el Modal)
    preferred_collaborator_ids: List[int] = Field(default_factory=list, description="Lista de IDs de colaboradores favoritos")

class ClientCreate(ClientBase):
    business_id: Optional[int] = 1

class ClientUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None # String simple también aquí
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    source: Optional[str] = None
    current_service_id: Optional[int] = None
    current_collaborator_id: Optional[int] = None
    
    preferred_collaborator_ids: Optional[List[int]] = None
    metadata_json: Optional[Dict[str, Any]] = None

class ClientResponse(ClientBase): 
    id: int
    business_id: int
    metadata_json: Dict[str, Any] = {}
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode='before')
    @classmethod
    def extract_favorites_from_metadata(cls, data: Any) -> Any:
        """
        Extrae los favoritos del JSONB para que el Frontend 
        los vea en la raíz del objeto cliente.
        """
        # Caso 1: Viene de SQLAlchemy (objeto con atributos)
        if hasattr(data, "metadata_json"):
            meta = data.metadata_json or {}
            favs = meta.get("preferred_collaborator_ids", [])
            setattr(data, "preferred_collaborator_ids", favs)
        
        # Caso 2: Viene como diccionario
        elif isinstance(data, dict):
            meta = data.get("metadata_json", {}) or {}
            data["preferred_collaborator_ids"] = meta.get("preferred_collaborator_ids", [])
            
        return data