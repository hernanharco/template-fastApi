from sqlalchemy.orm import Session
from app.models.clients import Client

def get_or_create_client_by_phone(db: Session, phone: str, full_name: str = None):
    """
    Busca un cliente por teléfono. Si no existe y tenemos el nombre, lo crea.
    """
    client = db.query(Client).filter(Client.phone == phone).first()
    
    if not client and full_name:
        client = Client(
            full_name=full_name,
            phone=phone,
            business_id=1, # Por ahora hardcoded como en tu modelo
            source="ia"
        )
        db.add(client)
        db.commit()
        db.refresh(client)
    
    return client