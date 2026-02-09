import os
import json
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Importamos tu lógica de base de datos y disponibilidad
from app.db.session import SessionLocal
from app.utils.availability import get_available_slots

# Cargamos variables de entorno para la API KEY
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Definición de herramientas para la IA (Function Calling)
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_availability",
            "description": "Consulta los horarios disponibles para un servicio en una fecha específica.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service_id": {
                        "type": "integer", 
                        "description": "El ID del servicio (ej: 3 para corte de cabello)"
                    },
                    "target_date": {
                        "type": "string", 
                        "description": "La fecha deseada en formato YYYY-MM-DD (ej: 2026-02-05)"
                    }
                },
                "required": ["service_id", "target_date"]
            }
        }
    }
]

def run_booking_agent(user_prompt: str):
    """
    Orquestador que recibe el mensaje del usuario, decide si llamar a la DB 
    y genera una respuesta en lenguaje natural.
    """
    messages = [
        {
            "role": "system", 
            "content": "Eres un asistente amable de una peluquería. Si el usuario pregunta por disponibilidad, usa la herramienta get_availability."
        },
        {"role": "user", "content": user_prompt}
    ]
    
    # 1. Primera llamada a la IA para analizar la intención
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=TOOLS,
        tool_choice="auto"
    )
    
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    # 2. Si la IA decide que necesita consultar la base de datos (Neon)
    if tool_calls:
        messages.append(response_message)
        
        for tool_call in tool_calls:
            # Extraemos los argumentos que la IA generó
            function_args = json.loads(tool_call.function.arguments)
            
            # --- CORRECCIÓN DE TIPOS Y NOMBRES ---
            raw_date = function_args.get("target_date")
            s_id = function_args.get("service_id")
            
            # Convertimos el string a objeto datetime (requerido por availability.py)
            date_obj = datetime.strptime(raw_date, "%Y-%m-%d")
            
            db = SessionLocal()
            try:
                # Llamada con los nombres exactos: target_date y service_id
                slots_data = get_available_slots(
                    db=db, 
                    target_date=date_obj,  # Nombre exacto del parámetro en tu clase
                    service_id=s_id
                )
                
                # Añadimos el resultado de la función al historial para la IA
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": "get_availability",
                    "content": json.dumps(slots_data, default=str), # default=str maneja fechas en el JSON
                })
                
                # 3. Segunda llamada a la IA para que redacte la respuesta final
                second_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                )
                return second_response.choices[0].message.content
                
            except Exception as e:
                return f"Error al consultar la agenda: {str(e)}"
            finally:
                db.close()

    # Si no hubo llamada a herramientas, devolver respuesta normal
    return response_message.content