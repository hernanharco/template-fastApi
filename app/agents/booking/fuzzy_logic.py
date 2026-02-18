from sqlalchemy.orm import Session
from thefuzz import process, fuzz
# IMPORTANTE: Cargamos los modelos relacionados para evitar el KeyError 'Client'
from app.models.services import Service 
from app.models.clients import Client       
from app.models.appointments import Appointment 

def service_fuzzy_match(db: Session, user_input: str, threshold: int = 60):
    """
    SRP: Traducir lenguaje natural del usuario a registros oficiales de la DB.
    Consulta directa a NEON para normalización.
    """
    if not user_input: 
        return None
        
    print(f"📡 [FUZZY] Buscando coincidencia para: '{user_input}'")
    
    # Al consultar Service, SQLAlchemy inicializa los mappers. 
    # Al tener Client y Appointment importados arriba, ya no se 'pierde'.
    services_db = db.query(Service).filter(Service.is_active == True).all()
    choices = {s.name: s.id for s in services_db}
    
    if not choices:
        print("⚠️ [FUZZY] No hay servicios activos en la DB.")
        return None

    query = user_input.lower()
    match = process.extractOne(query, choices.keys(), scorer=fuzz.WRatio)
    
    if match and match[1] >= threshold:
        print(f"🎯 [FUZZY] Encontrado: '{match[0]}' (Score: {match[1]})")
        return match[0], choices[match[0]] # Retorna (NombreOficial, ID)
        
    return None