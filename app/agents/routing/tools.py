# Las funciones reales (leer base de datos Neon)

# app/agents/routing/tools.py
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.clients import Client # Tu modelo de SQLAlchemy
from rich.console import Console

console = Console()

def create_new_client(phone: str, full_name: str = "Nuevo Cliente"):
    """
    Registra un nuevo cliente en Neon (PostgreSQL).
    """
    db = SessionLocal()
    try:
        # Siguiendo tu lógica de negocio: business_id por defecto 1 o dinámico
        new_client = Client(
            phone=phone,
            full_name=full_name,
            source="ia",
            is_active=True,
            business_id=1 
        )
        db.add(new_client)
        db.commit()
        db.refresh(new_client)
        console.print(f"[green]✅ Cliente creado:[/green] {phone}")
        return new_client
    except Exception as e:
        db.rollback()
        console.print(f"[red]❌ Error creando cliente:[/red] {e}")
        return None
    finally:
        db.close()

def update_client_name(phone: str, new_name: str):
    """
    Actualiza el nombre del cliente en Neon cuando este nos lo dice.
    """
    db = SessionLocal()
    try:
        client = db.query(Client).filter(Client.phone == phone).first()
        if client:
            client.full_name = new_name
            db.commit()
            console.print(f"[blue]🔄 Nombre actualizado:[/blue] {phone} -> {new_name}")
            return "Cliente no encontrado"
        return False
    except Exception as e:
        db.rollback()
        return False
    finally:
        db.close()