import json
from datetime import date
from openai import OpenAI
from rich import print as rprint
from app.core.settings import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)

def extract_booking_intent(user_msg: str, history_text: str = ""):
    """
    SRP: Transforma lenguaje natural en datos estructurados de reserva.
    PARCHE DEFINITIVO: Captura límites horarios (antes de/después de) y operadores.
    """
    hoy = date.today()
    formato_hoy = hoy.strftime("%A %d de %B de %Y")
    
    prompt = f"""
    Eres un extractor de entidades experto para una peluquería.
    Tu misión es convertir el mensaje del usuario en un JSON estructurado.

    HOY ES: {formato_hoy}.
    HISTORIAL RECIENTE: "{history_text}"
    MENSAJE ACTUAL: "{user_msg}"
    
    REGLAS DE EXTRACCIÓN:
    1. FECHA (date): Formato YYYY-MM-DD. Mantenla si el usuario no pide cambiarla.
    2. PREFERENCIA (preferencia): "manana", "tarde", "indiferente".
    
    3. LÓGICA HORARIA:
       - hora_limite: La hora mencionada en formato 24h (HH:MM).
       - operador:
         - "mayor_que": Si dice "después de", "luego de", "a partir de las...".
         - "menor_que": Si dice "antes de", "temprano", "que no pase de las...".
         - "exacto": Si dice "a las...", "justo a las...".
         - null: Si no hay restricción horaria clara.

    4. REINTENTO (es_reintento): true si está ajustando búsqueda tras no encontrar cupo.

    RESPONDE ÚNICAMENTE EL OBJETO JSON:
    {{
        "date": "YYYY-MM-DD",
        "preferencia": "manana" | "tarde" | "indiferente",
        "hora_limite": "HH:MM" | null,
        "operador": "mayor_que" | "menor_que" | "exacto" | null,
        "es_reintento": boolean
    }}
    """
    
    try:
        rprint(f"[cyan]🧠 Analizando intención de reserva: '{user_msg}'[/cyan]")
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Solo respondes JSON puro."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" },
            temperature=0
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        
        rprint(f"[bold yellow]IA BOOKING EXTRACTOR:[/bold yellow] {data}")
        return data

    except Exception as e:
        rprint(f"[bold red]❌ Error en Extractor Booking:[/bold red] {e}")
        return {
            "date": hoy.isoformat(), 
            "preferencia": "indiferente", 
            "hora_limite": None, 
            "operador": None, 
            "es_reintento": False
        }