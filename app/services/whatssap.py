# app/services/whatsapp.py
import httpx
from app.core.config import settings
from rich.console import Console

console = Console()

async def send_whatsapp_message(to_phone: str, message: str):
    """
    Envía un mensaje de texto plano a través de la API de WhatsApp Cloud.
    """
    url = f"https://graph.facebook.com/v22.0/{settings.PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_phone,
        "type": "text",
        "text": {"body": message}
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            console.print(f"[green]✅ Mensaje enviado a {to_phone}[/green]")
            return response
        except httpx.HTTPStatusError as e:
            console.print(f"[red]❌ Error de Meta API: {e.response.text}[/red]")
            return e.response
        except Exception as e:
            console.print(f"[red]❌ Error inesperado: {str(e)}[/red]")
            return None

async def send_presence(to_phone: str, status: str):
    """
    Marcamos como leído (READ) ya que Meta no permite typing_on fácilmente.
    """
    # Si status es 'typing_on', intentamos marcar como leído para que el usuario 
    # vea que recibimos el mensaje (doble check azul).
    if status == "typing_on":
        # Nota: Para marcar como leído se necesita el MESSAGE_ID, 
        # por ahora lo dejamos vacío para no generar errores en el log.
        pass
    
    # console.print(f"[blue]ℹ️ Info: Presencia saltada (Limitación de Meta API)[/blue]")
    return None

async def send_whatsapp_template(to_phone: str, template_name: str, components: list):
    """
    Envía plantillas pre-aprobadas.
    """
    url = f"https://graph.facebook.com/v22.0/{settings.PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": "es"},
            "components": components
        }
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, headers=headers)
            return response
        except Exception as e:
            console.print(f"[red]❌ Error en plantilla: {str(e)}[/red]")
            return None