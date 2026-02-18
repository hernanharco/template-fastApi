import json
import os
from datetime import datetime
from openai import OpenAI
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from app.models.services import Service

# [cite: 2026-02-18] Cargamos el entorno para asegurar disponibilidad de llaves
load_dotenv()

def get_openai_client():
    """
    Helper para inicializar el cliente solo cuando se necesita.
    Esto evita errores de importación en Uvicorn.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # [cite: 2026-01-30] Explicación: Lanzamos un error descriptivo si falta la Key.
        raise ValueError("❌ Error: OPENAI_API_KEY no encontrada. Revisa tu archivo .env")
    return OpenAI(api_key=api_key)

def master_extractor(db: Session, message: str, current_state: dict):
    """
    SRP: Centraliza la interpretación de lenguaje natural.
    [cite: 2026-02-13] Responsabilidad única: Extraer datos del mensaje.
    """
    # Inicialización segura dentro de la función
    client_ai = get_openai_client()

    # 1. Obtener servicios activos de NEON
    servicios_db = db.query(Service).filter(Service.is_active == True).all()
    nombres_catalog = [s.name for s in servicios_db]
    
    hoy = datetime.now()
    hoy_str = hoy.strftime("%Y-%m-%d (%A)")

    # 2. Configurar el Prompt (Reglas de Oro de Valeria)
    system_prompt = f"""
    Eres Valeria, la asistente inteligente de una clínica de estética. 
    Tu objetivo es extraer información técnica del mensaje del usuario.

    CONTEXTO ACTUAL:
    - Hoy es: {hoy_str}
    - Catálogo Real: {nombres_catalog}
    - Memoria actual del cliente (Neon): {current_state}

    INSTRUCCIONES DE EXTRACCIÓN (REGLAS DE ORO):
    1. 'intent': 
       - 'agendar': SOLO si el usuario quiere reservar AHORA (ej: "quiero cita", "dame turno").
       - 'saludo': Saludos, despedidas o si pospone (ej: "hola", "luego te escribo", "mañana hablamos").
       - 'ver_catalogo': Si pregunta qué haces o cuánto cuesta.
    2. 'service': Mapear al catálogo. Si no es claro, null.
    3. 'date': Fecha YYYY-MM-DD. SOLO si intent es 'agendar'. Si dice "mañana te escribo", date es null.
    4. 'time': HH:MM o null.
    5. 'min_time': '08:00', '13:00' o '18:00' según la jornada mencionada.

    IMPORTANTE: Si el usuario dice que escribirá después o solo saluda, el intent SIEMPRE es 'saludo'.
    Responde estrictamente en JSON.
    """

    # 3. Llamada al LLM
    response = client_ai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Mensaje: {message}"}
        ],
        response_format={"type": "json_object"},
        temperature=0
    )

    return json.loads(response.choices[0].message.content)