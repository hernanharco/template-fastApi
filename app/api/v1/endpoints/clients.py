from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db # Tu función para obtener la sesión
from app.models.clients import Client
from app.schemas.client import ClientResponse

router = APIRouter()

@router.get("/search/{phone}", response_model=ClientResponse)
def search_client_by_phone(phone: str, db: Session = Depends(get_db)):
    # Buscamos el primero que coincida con el teléfono
    client = db.query(Client).filter(Client.phone == phone).first()
    
    if not client:
        # Si no existe, lanzamos un 404 (esto lo capturaremos en Svelte)
        raise HTTPException(status_code=404, detail="Client not found")
        
    return client