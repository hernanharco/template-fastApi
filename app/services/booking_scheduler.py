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

def _get_favorites(client: Client) -> list:
    """
    Extrae preferred_collaborator_ids de metadata_json de forma segura.
    Maneja tanto dict como string JSON.
    """
    import json

    raw = client.metadata_json
    if not raw:
        return []

    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []

    # Soporta tanto {"preferred_collaborator_ids": [...]}
    # como {"profile": {"preferred_collaborator_ids": [...]}}
    if "preferred_collaborator_ids" in raw:
        return raw["preferred_collaborator_ids"]

    if "profile" in raw and isinstance(raw["profile"], dict):
        return raw["profile"].get("preferred_collaborator_ids", [])

    return []

def _apply_hour_filter(slots: List[Dict], min_hour: Optional[int], max_hour: Optional[int]) -> List[Dict]:
    """
    Filtra slots por rango horario antes de tomar los primeros 2.
    min_hour: hora mínima inclusiva (ej: 15 para "después de las 3pm")
    max_hour: hora máxima exclusiva (ej: 12 para "antes de las 12")
    """
    if min_hour is None and max_hour is None:
        return slots

    filtered = []
    for slot in slots:
        hour = slot["start_time"].hour
        if min_hour is not None and hour < min_hour:
            continue
        if max_hour is not None and hour >= max_hour:
            continue
        filtered.append(slot)
    return filtered


def get_booking_options_with_favorites(
    db: Session,
    client_phone: str,
    service_id: int,
    target_date: Optional[date] = None,
    min_hour: Optional[int] = None,   # filtro "después de las X"
    max_hour: Optional[int] = None,   # filtro "antes de las X"
    limit: Optional[int] = 2,         # None = sin límite (para first/last)
) -> Dict:
    """
    Obtiene opciones de reserva priorizando colaboradores favoritos del cliente.
    Devuelve exactamente 2 opciones para que el usuario elija.

    Parámetros de filtro horario:
    - min_hour: devuelve solo slots con hora >= min_hour (ej: 15 → después de las 3pm)
    - max_hour: devuelve solo slots con hora < max_hour  (ej: 12 → antes de las 12)
    """

    # 1. Obtener cliente y sus favoritos
    client = db.query(Client).filter(Client.phone == client_phone).first()
    if not client:
        rprint("[red]❌ Cliente no encontrado[/red]")
        return {"error": "Cliente no encontrado"}

    favorites = _get_favorites(client)
    rprint(f"[cyan]📋 Favoritos del cliente {client.full_name}: {favorites}[/cyan]")

    # 2. Obtener información del servicio
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        rprint("[red]❌ Servicio no encontrado[/red]")
        return {"error": "Servicio no encontrado"}

    # 3. Determinar fecha objetivo
    if not target_date:
        target_date = date.today()

    rprint(f"[blue]🎯 Buscando disponibilidad para:[/blue] {service.name} el {target_date}")
    if min_hour is not None:
        rprint(f"[blue]⏱ Filtro horario:[/blue] desde las {min_hour:02d}:00h")
    if max_hour is not None:
        rprint(f"[blue]⏱ Filtro horario:[/blue] hasta las {max_hour:02d}:00h")

    options = []

    # Estrategia 1: Favoritos
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

        favorite_slots = _apply_hour_filter(favorite_slots, min_hour, max_hour)
        favorite_slots.sort(key=lambda x: x["start_time"])
        options.extend(favorite_slots if limit is None else favorite_slots[:limit])

    # Estrategia 2: Cualquier colaborador si no hay suficientes
    if len(options) < 2:
        rprint(f"[yellow]🔍 Buscando con cualquier colaborador disponible...[/yellow]")
        all_slots = get_available_slots(
            db=db, target_date=target_date, service_id=service_id
        )

        # Aplicar filtro horario ANTES de tomar los primeros 2
        all_slots = _apply_hour_filter(all_slots, min_hour, max_hour)

        existing_start_times = {opt["start_time"] for opt in options}
        additional_slots = [
            slot for slot in all_slots if slot["start_time"] not in existing_start_times
        ]
        additional_slots.sort(key=lambda x: x["start_time"])

        if limit is None:
            options.extend(additional_slots)
        else:
            remaining_needed = limit - len(options)
            options.extend(additional_slots[:remaining_needed])

    # 5. Sin resultados
    if not options:
        # Si teníamos filtro, informar que no hay en ese rango
        filter_info = ""
        if min_hour is not None:
            filter_info = f" después de las {min_hour:02d}:00h"
        elif max_hour is not None:
            filter_info = f" antes de las {max_hour:02d}:00h"

        return {
            "success": False,
            "message": f"No hay disponibilidad para {service.name} el {target_date.strftime('%d/%m/%Y')}{filter_info}",
            "service": service.name,
            "date": target_date.strftime("%d/%m/%Y"),
            "has_hour_filter": min_hour is not None or max_hour is not None,
        }

    # 6. Formatear las 2 opciones
    formatted_options = []
    cap = limit if limit is not None else len(options)
    for i, slot in enumerate(options[:cap], 1):
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
    """Busca disponibilidad en los próximos días si no hay slots hoy."""
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
    """Confirma y crea la cita para la opción seleccionada."""
    try:
        appointment_datetime = datetime.strptime(selected_datetime, "%Y-%m-%d %H:%M")

        from app.core.config import settings
        import pytz

        tz = pytz.timezone(settings.APP_TIMEZONE)
        appointment_datetime = tz.localize(appointment_datetime)

        service = db.query(Service).filter(Service.id == service_id).first()
        if not service:
            return {"success": False, "error": "Servicio no encontrado"}

        end_time = appointment_datetime + timedelta(minutes=service.duration_minutes)

        now = datetime.now(tz)
        if appointment_datetime <= now:
            return {
                "success": False,
                "error": "La fecha seleccionada ya pasó. Por favor, elige una fecha futura.",
            }

        client = db.query(Client).filter(Client.phone == client_phone).first()
        if not client:
            return {"success": False, "error": "Cliente no encontrado"}

        appointment_data = AppointmentCreate(
            service_id=service_id,
            collaborator_id=collaborator_id,
            client_name=client.full_name,
            client_phone=client_phone,
            client_email=client.email,
            start_time=appointment_datetime,
            end_time=end_time,
            source="ia",
        )

        rprint(f"[blue]📅 Creando cita para {client.full_name} - {service.name}[/blue]")
        new_appointment = await appointment_manager.create_full_appointment(
            db, appointment_data
        )

        telegram_link = get_telegram_link(new_appointment.id)

        if telegram_link:
            message = (
                f"🎉 *¡Cita Agendada Exitosamente!*\n\n"
                f"📅 *Fecha y hora*: {appointment_datetime.strftime('%d/%m/%Y a las %H:%M')}\n"
                f"💇‍♀️ *Servicio*: {service.name}\n\n"
                f"📱 *Para tus recordatorios*:\n"
                f"Puedes gestionar tus recordatorios a través de Telegram:\n"
                f"{telegram_link}\n\n"
                f"¡Nos vemos pronto! 🌟"
            )
        else:
            message = (
                f"🎉 *¡Cita Agendada Exitosamente!*\n\n"
                f"📅 *Fecha y hora*: {appointment_datetime.strftime('%d/%m/%Y a las %H:%M')}\n"
                f"💇‍♀️ *Servicio*: {service.name}\n"
                f"👨‍💼 *Profesional*: ID {collaborator_id}\n"
                f"⏱️ *Duración*: {service.duration_minutes} minutos\n\n"
                f"¡Nos vemos pronto! 🌟"
            )

        rprint(f"[green]✅ Cita creada con ID: {new_appointment.id}[/green]")

        return {
            "success": True,
            "message": message,
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