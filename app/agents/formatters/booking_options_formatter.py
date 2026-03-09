# app/agents/formatters/booking_options_formatter.py

from typing import List, Dict


class BookingOptionsFormatter:
    """
    Formatter responsable de convertir opciones de booking
    en un mensaje conversacional para el usuario.

    SRP:
    - Solo formatea texto
    - No consulta DB
    - No contiene lógica de negocio
    """

    @staticmethod
    def format_options(service_name: str, date_text: str, options: List[Dict]) -> str:
        """
        Convierte las opciones de booking en texto para WhatsApp.

        Args:
            service_name: Nombre del servicio
            date_text: Fecha legible
            options: Lista de opciones de horario

        Returns:
            Mensaje formateado
        """

        if not options:
            return "No encontré horarios disponibles para ese día."

        lines = []

        lines.append(
            f"Tengo estas dos horas disponibles para *{service_name}* el {date_text}:"
        )
        lines.append("")

        for option in options:
            lines.append(f"{option['option_number']}. {option['time']}")

        lines.append("")
        lines.append("Responde con *1* o *2* para elegir tu horario.")

        return "\n".join(lines)

    @staticmethod
    def format_no_availability(service_name: str, date_text: str) -> str:
        """
        Mensaje cuando no hay disponibilidad.
        """

        return (
            f"No encontré horarios disponibles para *{service_name}* el {date_text}.\n\n"
            "¿Quieres probar otro día?"
        )