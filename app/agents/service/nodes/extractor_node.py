import os
import json
from openai import OpenAI
from sqlalchemy.orm import Session
from app.agents.agent_state import AgentState
from app.models.services import Service # Importamos el modelo [cite: 2026-02-07]

client_ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def service_extractor_node(db: Session, state: AgentState): # Añadimos db [cite: 2026-02-07]
    """
    Extrae el servicio usando el catálogo real de la base de datos.
    """
    # 1. CONSULTA REAL A NEON [cite: 2026-02-07]
    servicios_activos = db.query(Service).filter(Service.is_active == True).all()
    nombres_servicios = [s.name for s in servicios_activos]
    
    # Si no hay servicios, no podemos extraer nada
    if not nombres_servicios:
        return {"service_type": None}

    # 2. PROMPT DINÁMICO [cite: 2026-02-07, 2026-02-09]
    system_prompt = f"""
    Eres un experto en estética. Tu catálogo REAL y ÚNICO es: {nombres_servicios}.
    
    TAREA:
    Identifica cuál de estos servicios quiere el usuario.
    - Si el usuario dice un sinónimo (ej: 'manicura' para el servicio 'Uñas'), mapealo al nombre exacto del catálogo.
    - Si el usuario pide algo que NO está en la lista (ej: 'Masaje' y no está en la lista), responde con "service": null.
    
    Responde estrictamente en JSON:
    {{"service": "nombre_exacto_del_catálogo" o null}}
    """
    
    # 3. LLAMADA A LA IA [cite: 2026-02-07]
    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    
    response = client_ai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0
    )
    
    data = json.loads(response.choices[0].message.content)
    return {"service_type": data.get("service")}