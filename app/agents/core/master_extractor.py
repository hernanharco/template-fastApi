import json
import os
from datetime import datetime
from openai import OpenAI
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from app.models.services import Service

load_dotenv()


def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("❌ Error: OPENAI_API_KEY no encontrada.")
    return OpenAI(api_key=api_key)


def master_extractor(db: Session, message: str, current_state: dict):
    """
    SRP: Centraliza la interpretación de lenguaje natural.
    [cite: 2026-02-19] Parche aplicado: Reconocimiento de slots y rechazos.
    """
    client_ai = get_openai_client()

    servicios_db = db.query(Service).filter(Service.is_active == True).all()
    nombres_catalog = [s.name for s in servicios_db]

    hoy = datetime.now()
    hoy_str = hoy.strftime("%Y-%m-%d (%A)")

    # --- REGLAS DE REFUERZO ---
    system_prompt = f"""
    Eres Valeria, asistente de estética. Extrae información técnica del mensaje.

    CONTEXTO:
    - Hoy: {hoy_str}
    - Catálogo: {nombres_catalog}
    - Estado previo (Neon): {current_state}

    REGLAS DE ORO (ACTUALIZADAS):
    1. 'intent': 
       - 'agendar': Si quiere cita O si confirma una hora propuesta (ej: "16 esta bien", "el de las 10").
       - 'agendar': Si YA HAY un servicio en el estado previo y el usuario menciona cualquier servicio.
       - 'agendar': Si el usuario menciona fecha/hora explícita (mañana, lunes, jueves a las 11:00).
       - 'rechazo_disponibilidad': SOLO si dice "no me sirve", "ninguno", "tienes más tarde", "no puedo".
       - 'saludo': Saludos o si posterga la decisión.
       - 'ver_catalogo': Si pide explícitamente ver servicios, precios o catálogo PERO NO hay servicio previo.
    
    2. 'time': 
       - Si el usuario dice un número solo (ej: "16", "a las 4") y estamos agendando, conviértelo a HH:MM (16:00).
       - En horario comercial, "las 4" siempre es 16:00, "las 10" es 10:00.

    3. 'service': 
       - SOLO extraer si el usuario menciona CLARAMENTE un servicio del catálogo.
       - Si el mensaje es ambiguo como "quiero info", "disponibilidad", "mañana", NO extraer servicio.
       - Mantener el del estado previo si el usuario no menciona uno nuevo CLARAMENTE.

    IMPORTANTE: 
    - "quiero info" o "disponibilidad" NO mencionan un servicio específico -> service: null
    - Si el mensaje es "16 esta bien" y el servicio en memoria es 'Cejas', el intent debe ser 'agendar' y time '16:00'.
    - NO inventar servicios que no estén mencionados explícitamente.
    Responde estrictamente en JSON.
    """

    response = client_ai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Mensaje: {message}"},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    return json.loads(response.choices[0].message.content)
