from sqlalchemy.orm import Session
from app.agents.agent_state import AgentState
from app.models.services import Service

def service_validator_node(db: Session, state: AgentState):
    """
    Cruza el servicio extraído por la IA con la tabla de servicios en Neon.
    """
    extracted_name = state.get("service_type")
    
    if not extracted_name:
        return {"service_type": None}

    # Búsqueda flexible en la base de datos
    db_service = db.query(Service).filter(
        Service.name.ilike(f"%{extracted_name}%"),
        Service.is_active == True
    ).first()

    if db_service:
        print(f"✅ [Service Validator] Validado en DB: {db_service.name}")
        return {"service_type": db_service.name}
    
    print(f"⚠️ [Service Validator] '{extracted_name}' no existe en el catálogo.")
    return {"service_type": "not_found"}