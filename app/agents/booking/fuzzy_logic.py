# app/agents/booking/fuzzy_logic.py
from sqlalchemy.orm import Session
from thefuzz import process, fuzz
from app.models.services import Service
from rich import print as rprint

def service_fuzzy_match(db: Session, user_text: str, threshold: int = 60):
    """
    SRP: Lógica de coincidencia difusa para identificar servicios.
    Busca en la DB de Neon y compara con el texto del usuario.
    """
    # 1. Traer todos los servicios activos de la DB
    services = db.query(Service).filter(Service.is_active == True).all()
    if not services:
        return None

    # 2. Crear un diccionario de {Nombre: ID}
    service_map = {s.name: s.id for s in services}
    service_names = list(service_map.keys())

    # 3. Buscar la mejor coincidencia usando FuzzyWuzzy (thefuzz)
    # Comparamos el texto del usuario contra todos los nombres de servicios
    best_match, score = process.extractOne(user_text, service_names, scorer=fuzz.token_set_ratio)

    rprint(f"[yellow]🔍 Fuzzy Match: '{user_text}' -> '{best_match}' (Score: {score})[/yellow]")

    # 4. Si la coincidencia es buena (mayor al umbral), devolvemos el ID
    if score >= threshold:
        return best_match, service_map[best_match]
    
    return None