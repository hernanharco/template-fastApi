from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.clients import Client
from app.schemas.client import ClientCreate, ClientUpdate, ClientResponse

router = APIRouter()


@router.post("/", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(obj_in: ClientCreate, db: Session = Depends(get_db)):
    # 1. Verificar duplicados (esto está perfecto)
    existing = db.query(Client).filter(Client.phone == obj_in.phone).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este número de teléfono ya está registrado",
        )

    # 2. Extraemos los datos y LIMPIAMOS los que vamos a poner a mano
    client_data = obj_in.model_dump()

    # Quitamos business_id y source para que no choquen
    client_data.pop("business_id", None)
    client_data.pop("source", None)  # 👈 Esto es lo que te daba el error ahora

    # 3. Crear instancia limpia
    db_obj = Client(
        **client_data, business_id=1, source="manual"  # Ahora sí, aquí no hay choques
    )

    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj


@router.get("/", response_model=List[ClientResponse])
def read_clients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return (
        db.query(Client)
        .filter(Client.is_active == True)
        .order_by(Client.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int, client_in: ClientUpdate, db: Session = Depends(get_db)
):
    db_client = db.query(Client).filter(Client.id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    update_data = client_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_client, field, value)

    try:
        db.commit()
        db.refresh(db_client)
        return db_client
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al actualizar cliente")


@router.delete("/{client_id}")
def delete_client(client_id: int, db: Session = Depends(get_db)):
    db_obj = db.query(Client).filter(Client.id == client_id).first()
    if not db_obj:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    db_obj.is_active = False
    db.commit()
    return {"ok": True, "message": "Cliente desactivado"}
    
@router.get("/search/{phone}", response_model=ClientResponse) # 👈 Cambiado de ClientSchema a ClientResponse
def search_client_by_phone(phone: str, db: Session = Depends(get_db)):
    # 1. Buscamos en PostgreSQL (Neon)
    client = db.query(Client).filter(Client.phone == phone).first()
    
    # 2. Si no existe, lanzamos 404
    # Esto es correcto: el frontend recibirá null y permitirá escribir el nombre
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    return client