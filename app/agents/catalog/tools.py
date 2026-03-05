# app/agents/catalog/tools.py
from app.db.session import SessionLocal
from app.models.services import Service
from rich.console import Console

console = Console()

def get_services_catalog():
    """
    🎯 SRP: Única responsabilidad: Consultar datos crudos en la DB.
    Retorna una lista de diccionarios con la info de los servicios.
    """
    db = SessionLocal()
    try:
        # Buscamos solo los activos
        services = db.query(Service).filter(Service.is_active == True).all()
        
        if not services:
            return [] # Retornamos lista vacía si no hay nada
        
        # 🎯 IMPORTANTE: Devolvemos DATA estructurada, no texto.
        return [
            {
                "id": s.id, 
                "name": s.name, 
                "price": s.price, 
                "duration": s.duration_minutes
            } for s in services
        ]
        
    except Exception as e:
        console.print(f"[red]❌ Error al consultar catálogo en DB:[/red] {e}")
        return []
    finally:
        db.close()