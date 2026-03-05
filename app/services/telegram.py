# app/services/telegram.py
import httpx
from app.core.config import settings
from rich import print as rprint

def get_telegram_link(appointment_id: int) -> str:
    """
    Genera el enlace 'mágico' para saltar de WhatsApp a Telegram.
    """
    try:
        bot_name = settings.TELEGRAM_BOT_NAME
        if not bot_name or bot_name == "TuBot_bot":
            rprint("[yellow]⚠️ Telegram: TELEGRAM_BOT_NAME no configurado.[/yellow]")
            return ""
        return f"https://t.me/{bot_name}?start=apt_{appointment_id}"
    except Exception as e:
        rprint(f"[bold red]❌ Error generando link de Telegram:[/bold red] {e}")
        return ""

async def send_telegram_message(chat_id: str, text: str, reply_markup: dict = None):
    """
    Envía mensajes asíncronos por Telegram.
    Soporta reply_markup para enviar botones Inline opcionalmente.
    """
    if not settings.TELEGRAM_TOKEN:
        rprint("[red]❌ Error: TELEGRAM_TOKEN no encontrado.[/red]")
        return None

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }

    # Si enviamos botones, los añadimos al payload
    if reply_markup:
        payload["reply_markup"] = reply_markup

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            rprint(f"[bold red]❌ Telegram API Error:[/bold red] {e.response.text}")
        except Exception as e:
            rprint(f"[bold red]💥 Error de conexión con Telegram:[/bold red] {e}")
        return None