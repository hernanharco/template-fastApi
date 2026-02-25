# app/agents/appointments/extractor_confirmation.py
import re
from typing import Optional, Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from rich import print as rprint
from app.core.settings import settings

# Esquema para asegurar una salida estructurada (Pydantic v2)
class ConfirmationIntent(BaseModel):
    selection_type: str = Field(
        description="Tipo de selección: 'option_number', 'specific_time', 'text_confirmation' o 'unknown'"
    )
    value: Optional[str] = Field(
        description="El número de la opción (1, 2) o la hora detectada (HH:MM). NULL si no aplica."
    )
    raw_analysis: str = Field(description="Breve razonamiento de la extracción.")

def extract_confirmation_intent(user_msg: str, last_ai_msg: str) -> Dict[str, Any]:
    """
    Analiza la respuesta del usuario ante las opciones dadas por el bot.
    SRP: Transforma lenguaje natural de confirmación en datos estructurados.
    """
    
    # Configuramos el LLM con tu API Key de settings
    llm = ChatOpenAI(
        model="gpt-4o-mini", 
        temperature=0,
        api_key=settings.OPENAI_API_KEY 
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
        Eres un experto en extracción de datos para una agenda de citas de una peluquería/estética.
        Tu misión es identificar qué opción o qué hora eligió el usuario basándote en el mensaje de la IA.

        REGLAS DE ORO:
        1. SELECCIÓN POR NÚMERO ('option_number'): 
           - Si el usuario dice "la 1", "la primera", "opción 2", "el 1".
           - Value debe ser solo el dígito (ej: "1").

        2. HORA ESPECÍFICA ('specific_time'):
           - Si el usuario menciona una hora directamente: "a las 13:00", "a las 4", "7:30".
           - Value debe ser siempre HH:MM (ej: "16:00").
           - Si el usuario dice "a las 1" y en las opciones de la IA había una opción a las 13:00, interprétalo como 'specific_time' -> '13:00'.

        3. CONFIRMACIÓN SIMPLE ('text_confirmation'):
           - Si el usuario dice "si", "dale", "perfecto", "esa me sirve", "ok".
           - Esto indica que acepta la PRIMERA opción ofrecida por la IA si no especifica otra.

        4. DESCONOCIDO ('unknown'):
           - Si el usuario cambia de tema o dice algo incoherente con la reserva.

        RESPONDE SIEMPRE EN FORMATO JSON ESTRUCTURADO.
        """),
        ("human", "MENSAJE PREVIO DE IA (Opciones ofrecidas):\n{last_ai_msg}\n\nMENSAJE ACTUAL DEL USUARIO:\n{user_msg}")
    ])

    # Unimos el prompt con el modelo y forzamos la salida estructurada
    chain = prompt | llm.with_structured_output(ConfirmationIntent)
    
    try:
        rprint(f"[cyan]🧠 Analizando confirmación: '{user_msg}'[/cyan]")
        result = chain.invoke({
            "last_ai_msg": last_ai_msg,
            "user_msg": user_msg
        })
        
        rprint(f"[bold yellow]DEBUG Extractor Confirmation:[/bold yellow] {result.selection_type} -> {result.value}")
        return result.model_dump() # Usamos model_dump() en Pydantic v2
        
    except Exception as e:
        rprint(f"[bold red]❌ Error en Extractor Confirmation:[/bold red] {e}")
        # Fallback manual básico
        return {
            "selection_type": "unknown", 
            "value": None, 
            "raw_analysis": f"Error de API: {str(e)}"
        }