from datetime import datetime, timedelta
from app.models.reminder import ScheduledReminder

def create_appointment_reminders(db, appointment):
    """
    SRP: Clasifica la cita en un bloque de disparo para optimizar Neon.
    Ajuste: Incluye el texto de confirmación para interactuar vía Telegram/WhatsApp.
    """
    appo_hour = appointment.start_time.hour
    appo_date = appointment.start_time.date()

    # --- LÓGICA DE BLOQUES DE ANTICIPACIÓN ---
    
    # 1. Citas de la mañana (antes de la 1 PM): Se avisan a las 7 AM
    if appo_hour < 13:
        send_at = datetime.combine(appo_date, datetime.min.time()).replace(hour=7)
    
    # 2. Citas de la tarde (1 PM a 5 PM): Se avisan a las 11 AM
    elif 13 <= appo_hour < 17:
        send_at = datetime.combine(appo_date, datetime.min.time()).replace(hour=11)
    
    # 3. Citas del final del día (después de las 5 PM): Se avisan a las 3 PM
    else:
        send_at = datetime.combine(appo_date, datetime.min.time()).replace(hour=15)

    # --- VALIDACIÓN DE TIEMPO REAL ---
    now = datetime.now()
    
    # Si la cita se saca hoy para hoy y ya pasó la hora del bloque, 
    # se programa para "dentro de 1 minuto"
    if send_at < now:
        send_at = now + timedelta(minutes=1)

    # --- MENSAJE CON LÓGICA DE CONFIRMACIÓN ---
    # Al añadir la pregunta al final, el webhook de Telegram podrá procesar la respuesta.
    mensaje = (
        f"¡Hola {appointment.client_name}! ✨ Te recordamos tu cita en la "
        f"peluquería hoy a las {appointment.start_time.strftime('%H:%M')}.\n\n"
        "¿Confirmas tu asistencia? 👍\n"
        "(Responde *SÍ* para confirmar o *NO* para cancelar)"
    )

    # Creamos el recordatorio
    reminder = ScheduledReminder(
        appointment_id=appointment.id,
        phone=appointment.client_phone,
        message=mensaje,
        scheduled_for=send_at
    )

    db.add(reminder)
    # Nota: No hacemos db.commit() aquí, lo hace el nodo del agente.