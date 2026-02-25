# app/api/v1/endpoints/reminders.py
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import httpx
from rich import print as rprint
from rich.panel import Panel

from app.db.session import get_db 
from app.models.reminder import ScheduledReminder
from app.core.settings import settings
# 🚀 Servicio de Telegram actualizado que ya acepta reply_markup
from app.services.telegram import send_telegram_message 

router = APIRouter()

# Configuración de WhatsApp
WHATSAPP_TOKEN = settings.WHATSAPP_TOKEN
PHONE_NUMBER_ID = settings.PHONE_NUMBER_ID
WHATSAPP_URL = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"

@router.post("/process-batch", status_code=200)
async def process_reminders_batch(
    db: Session = Depends(get_db),
    x_cron_key: str = Header(None, alias="X-Cron-Key")
):
    """
    SRP: Endpoint para procesar y enviar recordatorios de forma híbrida.
    Ahora incluye botones de confirmación para los usuarios de Telegram.
    """
    
    # 🛡️ VALIDACIÓN DE SEGURIDAD
    if not x_cron_key or x_cron_key != settings.SECRET_KEY:
        rprint(f"[bold red]⚠️ [SECURITY] Acceso denegado: {datetime.now()}[/bold red]")
        raise HTTPException(status_code=403, detail="Token de autorización inválido.")

    now = datetime.now()

    rprint(Panel(
        f"[bold blue]⏰ PROCESANDO COLA DE RECORDATORIOS[/bold blue]\n"
        f"[cyan]Fecha/Hora:[/cyan] {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"[cyan]Canales:[/cyan] WhatsApp + Telegram (Prioridad con Botones)",
        title="[bold white]CRON JOB BATCH[/bold white]",
        border_style="green"
    ))

    # 🔍 BUSCAMOS LO QUE TOCA ENVIAR AHORA
    pending_reminders = (
        db.query(ScheduledReminder)
        .filter(
            ScheduledReminder.scheduled_for <= now, 
            ScheduledReminder.sent == False
        )
        .all()
    )

    if not pending_reminders:
        rprint("[yellow]ℹ️ No hay mensajes pendientes en la cola.[/yellow]")
        return {"status": "success", "processed": 0}

    # 🔘 DEFINICIÓN DE BOTONES PARA TELEGRAM
    # Estos botones enviarán 'callback_data' que nuestro webhook ya sabe procesar
    inline_buttons = {
        "inline_keyboard": [
            [
                {"text": "✅ Sí, confirmo", "callback_data": "confirm_yes"},
                {"text": "❌ No puedo ir", "callback_data": "confirm_no"}
            ]
        ]
    }

    sent_count = 0
    
    async with httpx.AsyncClient() as client:
        for reminder in pending_reminders:
            try:
                # --- 🚀 LÓGICA DE CANAL (Ahorro Modular) ---
                
                # Caso 1: Telegram (Ahorro total + Interactividad con botones)
                if reminder.telegram_chat_id and reminder.prefer_channel == "telegram":
                    rprint(f"✈️ [Telegram] Enviando recordatorio con botones a ID: {reminder.telegram_chat_id}")
                    
                    # Pasamos el reply_markup para que aparezcan los botones
                    success = await send_telegram_message(
                        chat_id=reminder.telegram_chat_id, 
                        text=reminder.message,
                        reply_markup=inline_buttons
                    )
                    
                    if success:
                        reminder.sent = True
                        reminder.sent_at = now
                        sent_count += 1
                        rprint(f"  [bold green]✅ OK:[/bold green] Telegram enviado con botones.")
                    else:
                        rprint(f"  [bold yellow]⚠️ Falló Telegram para ID {reminder.telegram_chat_id}.[/bold yellow]")

                # Caso 2: WhatsApp (Fallback - Sin botones por ahora para evitar costos extras de templates)
                else:
                    rprint(f"🚀 [WhatsApp] Enviando a {reminder.phone}...")
                    payload = {
                        "messaging_product": "whatsapp",
                        "to": reminder.phone,
                        "type": "text",
                        "text": {"body": reminder.message}
                    }
                    headers = {
                        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
                        "Content-Type": "application/json"
                    }
                    
                    response = await client.post(WHATSAPP_URL, json=payload, headers=headers)
                    
                    if response.status_code == 200:
                        reminder.sent = True
                        reminder.sent_at = now
                        sent_count += 1
                        rprint(f"  [bold green]✅ OK:[/bold green] WhatsApp enviado.")
                    else:
                        rprint(f"  [bold red]❌ Error Meta API ({response.status_code}):[/bold red] {response.text}")

            except Exception as e:
                rprint(f"  [bold red]💥 Error Crítico en Recordatorio {reminder.id}:[/bold red] {str(e)}")

    db.commit()

    rprint(Panel(
        f"[bold green]✨ Lote finalizado[/bold green]\n"
        f"Enviados: [bold white]{sent_count}[/bold white] / Pendientes: [bold white]{len(pending_reminders)}[/bold white]",
        border_style="blue"
    ))

    return {
        "status": "success",
        "processed": sent_count,
        "timestamp": now.isoformat()
    }