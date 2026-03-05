from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.clients import Client
from app.schemas.client import ClientCreate, ClientUpdate, ClientResponse

router = APIRouter()

@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(obj_in: ClientCreate, db: Session = Depends(get_db)):
    # 1. Verificar duplicados por teléfono
    existing = db.query(Client).filter(Client.phone == obj_in.phone).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este número de teléfono ya está registrado",
        )

    # 2. Extraer datos y manejar el campo virtual de favoritos
    # Sacamos preferred_collaborator_ids porque no existe como columna en la DB
    client_data = obj_in.model_dump(exclude={"preferred_collaborator_ids"})
    favorites = obj_in.preferred_collaborator_ids or []

    # 3. Preparar el objeto de base de datos
    db_obj = Client(**client_data)
    
    # Inyectamos los favoritos en el JSONB
    db_obj.metadata_json = {"preferred_collaborator_ids": favorites}
    
    # Valores por defecto para el MVP
    if not db_obj.business_id:
        db_obj.business_id = 1
    if not db_obj.source:
        db_obj.source = "manual"

    try:
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    except Exception as e:
        db.rollback()
        print(f"Error al crear cliente: {e}")
        raise HTTPException(status_code=500, detail="No se pudo crear el cliente")


@router.get("/", response_model=List[ClientResponse])
def read_clients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # Solo clientes activos, ordenados por los más recientes
    clients = (
        db.query(Client)
        .filter(Client.is_active == True)
        .order_by(Client.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    # SQLAlchemy cargará el metadata_json automáticamente. 
    # Pydantic en ClientResponse se encargará de mapear preferred_collaborator_ids 
    # si decides añadir un alias o propiedad, pero por ahora devolvemos el objeto tal cual.
    return clients


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int, client_in: ClientUpdate, db: Session = Depends(get_db)
):
    db_client = db.query(Client).filter(Client.id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # 1. Extraer datos (exclude_unset=True para no pisar campos con Nones)
    update_data = client_in.model_dump(exclude_unset=True)

    # 2. Manejar la actualización de favoritos en el JSON
    if "preferred_collaborator_ids" in update_data:
        new_favs = update_data.pop("preferred_collaborator_ids")
        # Mantener lo que ya había en metadata y solo actualizar los favoritos
        current_metadata = dict(db_client.metadata_json or {})
        current_metadata["preferred_collaborator_ids"] = new_favs
        db_client.metadata_json = current_metadata

    # 3. Actualizar el resto de campos dinámicamente
    for field, value in update_data.items():
        setattr(db_client, field, value)

    try:
        db.commit()
        db.refresh(db_client)
        return db_client
    except Exception as e:
        db.rollback()
        print(f"Error actualizando cliente: {e}")
        raise HTTPException(status_code=500, detail="Error interno al actualizar")


@router.get("/search/{phone}", response_model=ClientResponse)
def search_client_by_phone(phone: str, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.phone == phone).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client


@router.delete("/{client_id}")
def delete_client(client_id: int, db: Session = Depends(get_db)):
    db_obj = db.query(Client).filter(Client.id == client_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Soft Delete: Mantenemos la integridad referencial
    db_obj.is_active = False
    db.commit()
    return {"ok": True, "message": "Cliente desactivado correctamente"}