# app/api/v1/endpoints/telegram.py
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.reminder import ScheduledReminder
from app.services.telegram import send_telegram_message
from app.api.v1.endpoints.ai_whatsapp import process_message  # ← reutilizar el mismo handler
from rich import print as rprint

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def _get_phone_from_chat_id(chat_id: str, db: Session) -> str | None:
    """
    Busca el client_phone asociado a un chat_id de Telegram.
    Ruta: chat_id → ScheduledReminder → Appointment → client_phone
    """
    reminder = (
        db.query(ScheduledReminder)
        .filter(ScheduledReminder.telegram_chat_id == chat_id)
        .order_by(ScheduledReminder.id.desc())
        .first()
    )
    if reminder and reminder.appointment:
        return reminder.appointment.client_phone
    return None


@router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    data = await request.json()

    # --- 1. LÓGICA DE BOTONES (Callback Query) ---
    if "callback_query" in data:
        callback = data["callback_query"]
        callback_data = callback.get("data")
        chat_id = str(callback["message"]["chat"]["id"])

        rprint(f"[magenta]🔘 Botón pulsado: {callback_data} por chat {chat_id}[/magenta]")

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

    # --- Vinculación (Link Mágico /start) ---
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

    # --- 3. MENSAJE DE TEXTO LIBRE → MARÍA ---
    if text:
        rprint(f"[yellow]🧠 Mensaje para María vía Telegram:[/yellow] {text}")

        # Buscar el phone asociado al chat_id
        client_phone = await _get_phone_from_chat_id(chat_id, db)

        if not client_phone:
            # El usuario escribe por Telegram sin haber vinculado una cita antes
            await send_telegram_message(
                chat_id,
                "¡Hola! 👋 Para poder atenderte, primero agenda una cita por WhatsApp "
                "y luego activa los recordatorios por aquí con el enlace que te enviamos. 😊"
            )
            return {"status": "ok"}

        # Tiene phone → invocar a María igual que WhatsApp
        rprint(f"[green]📱 Phone encontrado:[/green] {client_phone}")
        await process_message(phone=client_phone, text=text)

    return {"status": "ok"}