# app/api/v1/endpoints/telegram.py
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.reminder import ScheduledReminder 
from app.services.telegram import send_telegram_message
from rich import print as rprint

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    
    # --- 1. LÓGICA DE BOTONES (Callback Query) ---
    # Esto se activa cuando el usuario toca "Confirmar" o "Cancelar" en el chat
    if "callback_query" in data:
        callback = data["callback_query"]
        callback_data = callback.get("data")
        chat_id = str(callback["message"]["chat"]["id"])
        
        rprint(f"[magenta]🔘 Botón pulsado: {callback_data} por chat {chat_id}[/magenta]")

        # Buscamos el recordatorio más reciente enviado a este chat
        reminder = db.query(ScheduledReminder).filter(
            ScheduledReminder.telegram_chat_id == chat_id,
            ScheduledReminder.sent == True
        ).order_by(ScheduledReminder.scheduled_for.desc()).first()

        if reminder and reminder.appointment:
            if callback_data == "confirm_yes":
                reminder.appointment.status = "confirmed"
                mensaje = "<b>¡Genial!</b> ✅ Tu cita ha sido confirmada. ¡Te esperamos!"
                rprint(f"[green]✅ Cita {reminder.appointment_id} CONFIRMADA vía botón[/green]")
            
            elif callback_data == "confirm_no":
                reminder.appointment.status = "cancelled"
                mensaje = "Entiendo. 😔 He <b>cancelado</b> tu cita. Si fue un error, por favor agenda de nuevo."
                rprint(f"[red]❌ Cita {reminder.appointment_id} CANCELADA vía botón[/red]")
            
            db.commit()
            await send_telegram_message(chat_id, mensaje)
            
        return {"status": "ok"}

    # --- 2. LÓGICA DE MENSAJES DE TEXTO ---
    message = data.get("message", {})
    text = str(message.get("text", "")).lower().strip()
    chat_id = str(message.get("chat", {}).get("id"))

    # Lógica de Vinculación (Link Mágico /start)
    if text.startswith("/start apt_"):
        appointment_id = text.replace("/start apt_", "")
        rprint(f"[cyan]🔗 Vinculando Cita {appointment_id} con Telegram {chat_id}[/cyan]")

        reminder = db.query(ScheduledReminder).filter(
            ScheduledReminder.appointment_id == appointment_id
        ).first()

        if reminder:
            reminder.telegram_chat_id = chat_id
            reminder.prefer_channel = "telegram" 
            db.commit()
            await send_telegram_message(
                chat_id, 
                "<b>¡Listo!</b> ✨ Recordatorios activados por aquí. Te avisaré antes de tu cita."
            )
        return {"status": "ok"}

    # --- 3. SI NO ES BOTÓN NI COMANDO, ES PARA MARÍA ---
    # Aquí es donde el mensaje de texto "suelto" se enviaría a LangGraph
    if text:
        rprint(f"[yellow]🧠 Mensaje para María:[/yellow] {text}")
        # respuesta_maria = await maria_agent.invoke(text, chat_id)
        # await send_telegram_message(chat_id, respuesta_maria)

    return {"status": "ok"}