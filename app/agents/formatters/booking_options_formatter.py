# app/agents/formatters/booking_options_formatter.py

from typing import List, Dict


class BookingOptionsFormatter:

    @staticmethod
    def format_options(service_name: str, date_text: str, options: List[Dict]) -> str:
        if not options:
            return "No encontré horarios disponibles para ese día."

        lines = []
        lines.append(
            f"👥 Tengo estas opciones disponibles para *{service_name}* el *{date_text}*:\n"
        )

        for option in options:
            lines.append(f"  *{option['option_number']}.* {option['time']}")

        reply_hint = BookingOptionsFormatter._build_reply_hint(options)
        lines.append(f"\nResponde {reply_hint} para confirmar tu elección.")

        return "\n".join(lines)

    @staticmethod
    def _build_reply_hint(options: List[Dict]) -> str:
        nums = [str(opt["option_number"]) for opt in options]
        if len(nums) == 1:
            return f"*{nums[0]}*"
        return ", ".join(f"*{n}*" for n in nums[:-1]) + f" o *{nums[-1]}*"

    @staticmethod
    def format_no_availability(service_name: str, date_text: str) -> str:
        return (
            f"No encontré horarios disponibles para *{service_name}* el *{date_text}*.\n\n"
            "¿Quieres probar otro día?"
        )