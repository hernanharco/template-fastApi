# app/services/booking_scheduler.py
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from rich import print as rprint

from app.models.clients import Client
from app.models.services import Service
from app.models.collaborators import Collaborator
from app.models.appointments import Appointment, AppointmentSource
from app.services.availability import get_available_slots
from app.services.appointment_manager import appointment_manager
from app.schemas.appointments import AppointmentCreate
from app.services.telegram import get_telegram_link
from rich import print as rprint


def get_booking_options_with_favorites(
    db: Session, client_phone: str, service_id: int, target_date: Optional[date] = None
) -> Dict:
    """
    SRP: Obtiene opciones de reserva priorizando colaboradores favoritos del cliente.
    Devuelve exactamente 2 opciones para que el usuario elija.
    """

    # 1. Obtener cliente y sus favoritos
    client = db.query(Client).filter(Client.phone == client_phone).first()
    if not client:
        rprint("[red]❌ Cliente no encontrado[/red]")
        return {"error": "Cliente no encontrado"}

    # Extraer IDs de colaboradores favoritos del metadata
    favorites = client.metadata_json.get("preferred_collaborator_ids", [])
    rprint(f"[cyan]📋 Favoritos del cliente {client.full_name}: {favorites}[/cyan]")

    # 2. Obtener información del servicio
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        rprint("[red]❌ Servicio no encontrado[/red]")
        return {"error": "Servicio no encontrado"}

    # 3. Determinar fecha objetivo (hoy si no se especifica)
    if not target_date:
        target_date = date.today()

    rprint(
        f"[blue]🎯 Buscando disponibilidad para:[/blue] {service.name} el {target_date}"
    )

    # 4. Estrategia de búsqueda: Primero favoritos, luego cualquiera
    options = []

    # Estrategia 1: Buscar slots con colaboradores favoritos
    if favorites:
        rprint(f"[yellow]⭐ Buscando con colaboradores favoritos...[/yellow]")
        favorite_slots = []

        for fav_id in favorites:
            slots = get_available_slots(
                db=db,
                target_date=target_date,
                service_id=service_id,
                collaborator_id=fav_id,
            )
            favorite_slots.extend(slots)

        # Ordenar por hora y tomar los primeros 2
        favorite_slots.sort(key=lambda x: x["start_time"])
        options.extend(favorite_slots[:2])

    # Estrategia 2: Si no hay suficientes opciones con favoritos, buscar con cualquiera
    if len(options) < 2:
        rprint(f"[yellow]🔍 Buscando con cualquier colaborador disponible...[/yellow]")
        all_slots = get_available_slots(
            db=db, target_date=target_date, service_id=service_id
        )

        # Filtrar slots que ya no estén en options
        existing_start_times = {opt["start_time"] for opt in options}
        additional_slots = [
            slot for slot in all_slots if slot["start_time"] not in existing_start_times
        ]
        additional_slots.sort(key=lambda x: x["start_time"])

        # Completar hasta tener 2 opciones
        remaining_needed = 2 - len(options)
        options.extend(additional_slots[:remaining_needed])

    # 5. Formatear respuesta
    if not options:
        return {
            "success": False,
            "message": f"No hay disponibilidad para {service.name} el {target_date.strftime('%d/%m/%Y')}",
            "service": service.name,
            "date": target_date.strftime("%d/%m/%Y"),
            "suggestions": [
                "¿Quieres probar otro día?",
                "¿Te gustaría ver la disponibilidad para mañana?",
            ],
        }

    # Formatear las 2 opciones
    formatted_options = []
    for i, slot in enumerate(options[:2], 1):
        collaborator = (
            db.query(Collaborator)
            .filter(Collaborator.id == slot["collaborator_id"])
            .first()
        )
        is_favorite = collaborator and collaborator.id in favorites

        option = {
            "option_number": i,
            "time": slot["start_time"].strftime("%H:%M"),
            "collaborator": (
                collaborator.name if collaborator else slot["collaborator_name"]
            ),
            "collaborator_id": slot["collaborator_id"],
            "is_favorite": is_favorite,
            "full_datetime": slot["start_time"].strftime("%Y-%m-%d %H:%M"),
            "duration_minutes": service.duration_minutes,
        }
        formatted_options.append(option)

    rprint(f"[green]✅ Opciones encontradas: {len(formatted_options)}[/green]")

    return {
        "success": True,
        "service": service.name,
        "service_id": service_id,
        "date": target_date.strftime("%d/%m/%Y"),
        "client": client.full_name,
        "has_favorites": len(favorites) > 0,
        "options": formatted_options,
        "selection_prompt": f"Por favor, selecciona una opción para tu cita de {service.name}:",
    }


def get_next_available_dates(
    db: Session, service_id: int, days_ahead: int = 3
) -> List[Dict]:
    """
    SRP: Busca disponibilidad en los próximos días si no hay slots hoy.
    """
    available_dates = []
    base_date = date.today()

    for day_offset in range(1, days_ahead + 1):
        check_date = base_date + timedelta(days=day_offset)
        slots = get_available_slots(db, check_date, service_id)

        if slots:
            available_dates.append(
                {
                    "date": check_date.strftime("%d/%m/%Y"),
                    "day_name": check_date.strftime("%A"),
                    "available_slots": len(slots),
                    "first_slot_time": slots[0]["start_time"].strftime("%H:%M"),
                }
            )

    return available_dates


async def confirm_booking_option(
    db: Session,
    client_phone: str,
    service_id: int,
    collaborator_id: int,
    selected_datetime: str,
) -> Dict:
    """
    SRP: Confirma y crea la cita para la opción seleccionada.
    Genera mensaje con enlace a Telegram para recordatorios.
    """
    try:
        # Parsear la fecha y hora seleccionada
        appointment_datetime = datetime.strptime(selected_datetime, "%Y-%m-%d %H:%M")

        # 🚀 FIX CRÍTICO: Añadir timezone a las fechas para que coincida con el modelo
        from app.core.config import settings
        import pytz

        tz = pytz.timezone(settings.APP_TIMEZONE)

        # Convertir a timezone-aware
        appointment_datetime = tz.localize(appointment_datetime)

        # Obtener información del servicio PRIMERO
        service = db.query(Service).filter(Service.id == service_id).first()
        if not service:
            return {"success": False, "error": "Servicio no encontrado"}

        # Calcular hora de fin basada en la duración del servicio
        end_time = appointment_datetime + timedelta(minutes=service.duration_minutes)

        # Validar que la cita sea en el futuro (comparar con timezone-aware)
        now = datetime.now(tz)
        if appointment_datetime <= now:
            return {
                "success": False,
                "error": "La fecha seleccionada ya pasó. Por favor, elige una fecha futura.",
            }

        # Obtener información del cliente
        client = db.query(Client).filter(Client.phone == client_phone).first()
        if not client:
            return {"success": False, "error": "Cliente no encontrado"}

        # Crear el objeto AppointmentCreate
        appointment_data = AppointmentCreate(
            service_id=service_id,
            collaborator_id=collaborator_id,
            client_name=client.full_name,
            client_phone=client_phone,
            client_email=client.email,
            start_time=appointment_datetime,
            end_time=end_time,
            source="ia",  # Indicar que la cita fue creada por la IA
        )

        # Crear la cita usando el AppointmentManager
        rprint(f"[blue]📅 Creando cita para {client.full_name} - {service.name}[/blue]")
        new_appointment = await appointment_manager.create_full_appointment(
            db, appointment_data
        )

        # Generar enlace de Telegram
        telegram_link = get_telegram_link(new_appointment.id)

        # Construir mensaje de confirmación con enlace a Telegram
        if telegram_link:
            telegram_message = f"""
                🎉 *¡Cita Agendada Exitosamente!*

                📅 *Fecha y hora*: {appointment_datetime.strftime('%d/%m/%Y a las %H:%M')}
                💇‍♀️ *Servicio*: {service.name}

                📱 *Para tus recordatorios*: 
                Puedes gestionar tus recordatorios y recordatorios automáticos a través de Telegram haciendo clic en este enlace:
                {telegram_link}

                ¡Nos vemos pronto! 🌟"""
        else:
            telegram_message = f"""
                🎉 *¡Cita Agendada Exitosamente!*

                📅 *Fecha y hora*: {appointment_datetime.strftime('%d/%m/%Y a las %H:%M')}
                💇‍♀️ *Servicio*: {service.name}
                👨‍💼 *Profesional*: ID {collaborator_id}
                ⏱️ *Duración*: {service.duration_minutes} minutos

                📱 *Para recordatorios*: 
                El servicio de recordatorios por Telegram estará disponible pronto. ¡Te avisaremos!

                ¡Nos vemos pronto! 🌟"""

        rprint(f"[green]✅ Cita creada con ID: {new_appointment.id}[/green]")

        return {
            "success": True,
            "message": telegram_message,
            "appointment": {
                "id": new_appointment.id,
                "service": service.name,
                "datetime": appointment_datetime.strftime("%d/%m/%Y a las %H:%M"),
                "collaborator_id": collaborator_id,
                "duration": service.duration_minutes,
                "status": new_appointment.status.value,
                "telegram_link": telegram_link,
            },
        }

    except ValueError as e:
        rprint(f"[red]❌ Error de formato: {e}[/red]")
        return {"success": False, "error": f"Formato de fecha inválido: {e}"}
    except Exception as e:
        rprint(f"[red]❌ Error al confirmar cita: {e}[/red]")
        return {"success": False, "error": f"Error al confirmar la cita: {e}"}
