from typing import List

from app.schemas.services import ServiceRead


def format_catalog_for_whatsapp(services: List[ServiceRead], client_name: str | None = None) -> str:
    if not services:
        if client_name:
            return f"{client_name}, ahora mismo no tengo servicios disponibles."
        return "Ahora mismo no tengo servicios disponibles."

    header = "Estos son algunos de los servicios disponibles 😊"
    if client_name:
        header = f"{client_name}, estos son algunos de los servicios disponibles 😊"

    lines = [header, ""]

    for service in services[:10]:
        line = f"• {service.name}"

        details = []
        # if service.duration_minutes:
        #     details.append(f"{service.duration_minutes} min")
        # if service.price is not None:
        #     details.append(f"${service.price:.2f}")

        if details:
            line += f" ({' · '.join(details)})"

        lines.append(line)

    lines.append("")
    lines.append("Dime cuál te interesa y te ayudo con los horarios.")

    return "\n".join(lines)