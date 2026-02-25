# app/services/whatsapp.py
import httpx
from app.core.settings import settings

async def send_whatsapp_message(to_phone: str, message: str):
    """
    Función limpia para enviar mensajes de texto plano.
    """
    url = f"https://graph.facebook.com/v22.0/{settings.PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": message}
    }
    
    async with httpx.AsyncClient() as client:
        return await client.post(url, json=payload, headers=headers)

async def send_whatsapp_template(to_phone: str, template_name: str, components: list):
    """
    Función para enviar las Plantillas (Templates) cuando pasan las 24h.
    """
    # Lógica similar pero con estructura de template...
    pass