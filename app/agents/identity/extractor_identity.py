# app/agents/identity/extractor_identity.py
from openai import OpenAI
from app.core.settings import settings
from rich import print as rprint

def extract_name_from_text(text: str) -> str:
    """
    Extractor mejorado para capturar nombres simples.
    """
    if not text or len(text.strip()) < 2:
        return "NONE"

    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Un prompt más flexible pero directo
        prompt = (
            f"Analiza este mensaje: '{text}'.\n"
            "Si el usuario indica su nombre, responde ÚNICAMENTE el nombre propio.\n"
            "Ejemplos:\n"
            "- 'Soy Hernán' -> Hernán\n"
            "- 'Hernán' -> Hernán\n"
            "- 'Me llamo Juan Carlos' -> Juan Carlos\n"
            "Si el mensaje es un saludo o no contiene un nombre, responde: NONE"
        )

        res = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            temperature=0,
            timeout=8
        )
        
        name = res.choices[0].message.content.strip()
        # Limpiamos posibles puntos finales que a veces pone la IA
        name = name.replace(".", "") 
        
        rprint(f"[cyan]🤖 Extractor IA dice:[/cyan] {name}")
        return name

    except Exception as e:
        rprint(f"[red]❌ Error en Extractor:[/red] {e}")
        return "NONE"