from typing import Literal, List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from app.core.settings import settings

class IntentSchema(BaseModel):
    # Añadimos greeting y farewell para mayor precisión
    intent: Literal["info", "booking", "confirmation", "greeting", "farewell", "other"] = Field(
        description="Clasificación de la intención del usuario para enrutado."
    )

def extract_intent(message: str, history: List[BaseMessage]) -> str:
    """Usa IA para determinar a qué nodo enviar al usuario."""
    llm = ChatOpenAI(
        model="gpt-4o-mini", 
        temperature=0,
        api_key=settings.OPENAI_API_KEY
    )
    structured_llm = llm.with_structured_output(IntentSchema)
    
    history_text = ""
    for m in history:
        role = "IA" if m.type == "ai" else "Usuario"
        history_text += f"{role}: {m.content}\n"
    
    prompt = f"""Analiza el mensaje del usuario considerando el contexto para elegir la mejor categoría:
    
    HISTORIAL:
    {history_text}
    
    MENSAJE ACTUAL:
    "{message}"
    
    CATEGORÍAS:
    - greeting: Saludos iniciales (ej: 'Hola', 'Buenos días', 'Buenas'). Solo si no hay una petición de cita inmediata.
    - farewell: Despedidas o agradecimientos finales (ej: 'Adiós', 'Muchas gracias', 'Chao', 'Ya terminé').
    - confirmation: Selección de opciones (1, 2, la primera), confirmación de hora ('a las 9 está bien') o confirmación de datos.
    - booking: Petición de cita, cambio de fecha o interés en un servicio específico.
    - info: Dudas sobre precios, servicios, dirección o cómo funciona el sistema.
    - other: Comentarios que no encajan en ninguna o mensajes sin sentido.
    """
    
    try:
        res = structured_llm.invoke(prompt)
        return res.intent
    except Exception:
        return "info"