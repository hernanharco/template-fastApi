# app/agents/appointments/appointment_confirmation_node.py
import re
import traceback
import asyncio # 🚀 1. Agregado para no bloquear a María
from datetime import datetime, timedelta, time
from langchain_core.messages import AIMessage
from rich import print as rprint

from app.db.session import SessionLocal
from app.agents.state import AgentState
from app.models.appointments import Appointment, AppointmentStatus
from app.models.clients import Client
from app.models.collaborators import Collaborator
from app.models.services import Service
from app.services.availability import find_available_collaborator, get_business_day_range
from app.agents.appointments.extractor_confirmation import extract_confirmation_intent
from app.services.reminder import create_appointment_reminders
# 🚀 2. Importación del helper de notificaciones
from app.api.v1.endpoints.notifications import notify_appointment_change

# Fragmento de lógica en el nodo de confirmación de María
from app.services.telegram import get_telegram_link

# --- 🛠️ FUNCIONES DE APOYO INTERNAS ---

def resolver_ambiguedad_pm(db, hora_cruda: str, fecha_cita: datetime) -> str:
    """
    SRP: Convierte horas como '1' o '1:00' a '13:00' si el local está abierto tarde.
    """
    try:
        hora_limpia = hora_cruda.replace('.', ':')
        if ':' not in hora_limpia:
            if len(hora_limpia) <= 2: hora_limpia += ":00"
        
        h, m = map(int, hora_limpia.split(':'))
        if h >= 12: return f"{h:02d}:{m:02d}"
        
        opening, closing = get_business_day_range(db, fecha_cita.weekday())
        if not opening: return f"{h:02d}:{m:02d}"

        if time(h, m) < opening:
            h_pm = h + 12
            if h_pm < 24 and (opening <= time(h_pm, m) <= closing):
                rprint(f"[yellow]🌙 Ajuste AM -> PM: {hora_cruda} a {h_pm}:{m:02d}[/yellow]")
                return f"{h_pm:02d}:{m:02d}"
        
        return f"{h:02d}:{m:02d}"
    except Exception:
        return hora_cruda

# --- 🤖 NODO PRINCIPAL ---

def appointment_confirmation_node(state: AgentState) -> dict:
    rprint("\n[bold cyan]💾 --- APPOINTMENT NODE START ---[/bold cyan]")
    
    db = SessionLocal()
    try:
        # 1. Recuperación de datos del estado
        messages = state.get("messages", [])
        user_msg = str(messages[-1].content).lower() if messages else ""
        service_id = state.get("service_id")
        phone = state.get("client_phone")

        # 2. Validación de Entidades (Cliente y Servicio)
        client = db.query(Client).filter(Client.phone == phone).first()
        
        # ✨ PARCHE DE SEGURIDAD: Buscamos el servicio por el ID que arrastramos en el estado
        srv = db.query(Service).filter(Service.id == service_id).first()

        if not srv:
            rprint("[red]⚠️ No se encontró el servicio con el ID proporcionado.[/red]")
            return {
                "messages": [AIMessage(content="¡Claro! Pero primero confírmame, ¿qué servicio te gustaría realizarte?")],
                "current_node": "service_expert"
            }
        
        if not client:
            return {"messages": [AIMessage(content="Lo siento, no logré identificar tu perfil. ¿Podemos empezar de nuevo?")]}

        # 3. RECUPERAR LA FECHA DEL HISTORIAL (Mirando hacia atrás en la conversación)
        target_date = None
        last_ai_msg = ""
        for msg in reversed(messages[:-1]):
            if isinstance(msg, AIMessage):
                if not last_ai_msg: last_ai_msg = msg.content
                # Buscamos patrones de fecha como 25/02 o 2026-02-25
                date_match = re.search(r"(\d{1,2})[/-]\d{1,2}|día\s*(\d{1,2})", msg.content.lower())
                if date_match:
                    day_found = int(date_match.group(1) or date_match.group(2))
                    # Ajustamos al mes/año actual para simplificar
                    target_date = datetime.now().replace(day=day_found, hour=0, minute=0, second=0, microsecond=0)
                    break
        
        if not target_date:
            target_date = datetime.now()

        # 4. EXTRACCIÓN INTELIGENTE DE LA SELECCIÓN
        intent = extract_confirmation_intent(user_msg, last_ai_msg)
        rprint(f"[yellow]DEBUG Extractor IA:[/yellow] {intent}")

        selected_time = None
        # Buscamos las opciones que la IA le ofreció anteriormente (formato HH:MM)
        horas_ofrecidas = re.findall(r"(\d{1,2}:\d{2})", last_ai_msg)

        if intent["selection_type"] == "option_number":
            idx = int(intent["value"]) - 1
            if 0 <= idx < len(horas_ofrecidas):
                selected_time = horas_ofrecidas[idx]
        
        elif intent["selection_type"] == "specific_time":
            selected_time = intent["value"]
        
        elif intent["selection_type"] == "text_confirmation":
            if horas_ofrecidas:
                selected_time = horas_ofrecidas[0]

        # Fallback de seguridad si el extractor no fue claro
        if not selected_time:
            time_match = re.search(r"(\d{1,2}[:.]\d{2})", user_msg)
            selected_time = time_match.group(1) if time_match else (horas_ofrecidas[0] if horas_ofrecidas else "12:00")

        # 5. PARCHE: RESOLUCIÓN DE AMBIGÜEDAD AM/PM (Ej: "a las 1" -> 13:00)
        selected_time = resolver_ambiguedad_pm(db, selected_time, target_date)

        # 6. CONSTRUCCIÓN DEL MOMENTO EXACTO
        hour, minute = map(int, selected_time.split(':'))
        appointment_start = target_date.replace(hour=hour, minute=minute)
        appointment_end = appointment_start + timedelta(minutes=srv.duration_minutes or 60)

        rprint(f"[yellow]⏳ Verificando disponibilidad final para {srv.name}: {appointment_start.strftime('%H:%M')}[/yellow]")

        # 7. BÚSQUEDA DINÁMICA DE COLABORADOR
        colab_id = find_available_collaborator(db, appointment_start, appointment_end, srv.id)
        
        if not colab_id:
            rprint("[red]❌ Slot ocupado o inválido en el último segundo.[/red]")
            return {"messages": [AIMessage(content="¡Vaya! Justo se acaban de llevar ese espacio. ¿Probamos con otro horario?")]}

        colab = db.query(Collaborator).filter(Collaborator.id == colab_id).first()

        # 8. PERSISTENCIA EN DB
        new_appointment = Appointment(
            client_id=client.id,
            service_id=srv.id,
            collaborator_id=colab.id,
            client_name=client.full_name,
            client_phone=client.phone,
            start_time=appointment_start,
            end_time=appointment_end,
            status=AppointmentStatus.SCHEDULED,
            source="ia"
        )
        
        db.add(new_appointment)
        db.flush() # Para obtener el ID antes del commit

        # 🚀 8.1 CREACIÓN DE RECORDATORIOS (Bloques 7/11/15)
        try:
            create_appointment_reminders(db, new_appointment)
            rprint("[blue]🔔 Recordatorios encolados con éxito.[/blue]")
        except Exception as e:
            rprint(f"[bold red]⚠️ Error al encolar recordatorios: {e}[/bold red]")

        db.commit()
        rprint(f"[green]✅ CITA CREADA ID: {new_appointment.id} ({srv.name})[/green]")

        # 🚀 8.2 GENERACIÓN DEL ENLACE MÁGICO (El Parche ✈️)             
        
        link_telegram = get_telegram_link(new_appointment.id)

        # 🚀 3. EL GRITO AL FRONTEND (Payload Premium)
        # Lo enviamos justo después del commit para que el dashboard se entere
        try:
            asyncio.create_task(
                notify_appointment_change(
                    client_name=client.full_name,
                    service_name=srv.name,
                    start_time=appointment_start.strftime('%H:%M')
                )
            )
            rprint("[blue]📡 Notificación enviada al dashboard (vía RAM).[/blue]")
        except Exception as e:
            rprint(f"[bold red]⚠️ Error notificando al dashboard: {e}[/bold red]")

        # 9. RESPUESTA FINAL PERSONALIZADA
        res = (
            f"¡Confirmado, {client.full_name}! 🎊\n\n"
            f"He reservado tu cita para *{srv.name}*.\n"
            f"🗓️ *Día:* {appointment_start.strftime('%d/%m/%Y')}\n"
            f"⏰ *Hora:* {appointment_start.strftime('%H:%M')}\n"
            f"🔔 *¿Quieres un recordatorio gratuito?*\n"
            f"Para no olvidar tu cita, activa los avisos aquí:\n"
            f"{link_telegram}\n\n"
            "¡Te esperamos! ✨"
        )

        return {
            "messages": [AIMessage(content=res)],
            "appointment_id": new_appointment.id,
            "service_id": None,
            "current_node": "appointment_confirmation"
        }

    except Exception as e:
        db.rollback()
        rprint(f"[bold red]🔥 ERROR EN CONFIRMACIÓN:[/bold red]\n{traceback.format_exc()}")
        return {"messages": [AIMessage(content="Hubo un pequeño problema técnico al guardar tu cita. ¿Podemos intentarlo de nuevo?")], "current_node": "appointment_confirmation"}
    finally:
        db.close()
        rprint("[bold cyan]💾 --- APPOINTMENT NODE END ---[/bold cyan]\n")