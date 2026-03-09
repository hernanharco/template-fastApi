from rich.console import Console
from rich.panel import Panel

console = Console()


def print_state_debug(state: dict):

    values = state.get("values", {})

    ids = values.get("shown_service_ids", [])
    slots = values.get("active_slots", [])
    name = values.get("client_name", "Desconocido")

    console.print(
        Panel(
            f"👤 Cliente: {name}\n"
            f"📦 IDs: {ids}\n"
            f"🕒 Slots: {len(slots)}",
            title="Estado del hilo",
        )
    )