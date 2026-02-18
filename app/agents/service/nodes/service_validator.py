from sqlalchemy.orm import Session
from app.models.services import Service
from thefuzz import process, fuzz

def service_validator_node(db: Session, extracted_data: dict):
    """
    Usa thefuzz para encontrar el servicio correcto incluso con errores graves.
    """
    input_service = extracted_data.get("service_type")
    
    if not input_service or str(input_service).lower() == "none":
        return {"service_type": None, "service_id": None}

    # 1. Traer servicios reales de Neon
    services_db = db.query(Service).filter(Service.is_active == True).all()
    services_dict = {s.name.lower(): (s.name, s.id) for s in services_db}
    
    target = str(input_service).lower().strip()
    choices = list(services_dict.keys())

    # 2. Búsqueda Difusa con Token Set Ratio (Ignora letras faltantes y orden)
    best_match, score = process.extractOne(
        target, 
        choices, 
        scorer=fuzz.token_set_ratio
    )
    
    print(f"📊 [THEFUZZ] Analizando: '{target}' -> Match: '{best_match}' ({score}%)")

    # Umbral del 60%: Suficiente para 'cote de cabelo' -> 'corte de cabello'
    if score >= 60:
        original_name, srv_id = services_dict[best_match]
        print(f"✅ [THEFUZZ] Servicio Validado: {original_name}")
        return {"service_type": original_name, "service_id": srv_id}

    print(f"❌ [THEFUZZ] No hay coincidencia clara para '{target}'")
    return {"service_type": "not_found", "service_id": None}