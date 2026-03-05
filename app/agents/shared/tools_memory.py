# app/agents/core/tools_memory.py
from langchain_core.tools import tool
import json
from app.db.session import AsyncSessionLocal 
from app.models.clients import Client 
from sqlalchemy.future import select
from rich.console import Console
from pydantic import BaseModel, Field

console = Console()

# ==============================================================================
# --- ESQUEMAS PYDANTIC ---
# ==============================================================================

# 🟢 ESQUEMA PARA ACTUALIZAR METADATA (Reemplaza a UpdateMemoryInput)
class UpdateMetadataInput(BaseModel):
    phone: str = Field(description="El número de teléfono del cliente")
    metadata_dict: dict = Field(description="Diccionario con los datos a actualizar en metadata_json")

# 🟢 ESQUEMA PARA LEER METADATA
class GetMetadataInput(BaseModel):
    phone: str = Field(description="El número de teléfono del cliente")

# ==============================================================================
# --- HERRAMIENTA 1: ACTUALIZAR METADATA (Reemplaza update_client_memory) ---
# ==============================================================================

@tool("update_client_metadata", args_schema=UpdateMetadataInput)
async def update_client_metadata(phone: str, metadata_dict: dict) -> str:
    """
    Actualiza el campo JSONB 'metadata_json' del cliente identificado por su teléfono.
    Úsalo para guardar preferencias, favoritos, estado de reserva, etc.
    
    Ejemplo: {"preferred_collaborator_ids": [1, 5], "last_service_id": 3}
    """
    console.print(f"[bold cyan]🎬 [TOOL]: update_client_metadata[/bold cyan] -> Entrada: {metadata_dict}")

    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(Client).where(Client.phone == phone))
            client = result.scalar_one_or_none()
            
            if not client:
                return "Cliente no encontrado"
                
            # 🟢 Usar metadata_json en lugar de memory
            current_metadata = client.metadata_json or {}
            current_metadata.update(metadata_dict)
            client.metadata_json = current_metadata
            
            await db.commit()
            
            console.print(f"[bold green]✅ Metadata actualizada para {client.full_name}[/bold green]")
            return f"Metadata actualizada para {client.full_name}"
        except Exception as e:
            await db.rollback()
            console.print(f"[bold red]❌ Error al actualizar metadata: {e}[/bold red]")
            return f"Error al actualizar metadata: {str(e)}"

# ==============================================================================
# --- HERRAMIENTA 2: OBTENER METADATA (Reemplaza get_client_memory) ---
# ==============================================================================

@tool("get_client_metadata", args_schema=GetMetadataInput)
async def get_client_metadata(phone: str) -> dict:
    """
    Recupera el objeto JSON de metadata de un cliente a partir de su teléfono.
    """
    console.print(f"[bold cyan]🎬 [TOOL]: get_client_metadata[/bold cyan] -> Teléfono: {phone}")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Client).where(Client.phone == phone))
        client = result.scalar_one_or_none()
        
        if not client:
            return {}
        
        # 🟢 Retornar metadata_json en lugar de memory
        return client.metadata_json or {}