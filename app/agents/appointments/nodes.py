import re
import logging
from rich import print as rprint
from langchain_core.messages import AIMessage

from app.agents.routing.state import RoutingState
from app.agents.appointments.tools import book_appointment_tool

logger = logging.getLogger(__name__)

async def confirmation_node(state: RoutingState):
    """
    🎯 SRP: Única responsabilidad: Validar la selección final del turno y 
    persistir la reserva en la base de datos (Neon/PostgreSQL).
    """
    # 1. Preparación de datos
    user_input = state["messages"][-1].content.lower().strip()
    active_slots = state.get("active_slots", [])
    service_id = state.get("selected_service_id")
    phone = state.get("client_phone")

    rprint(f"[bold cyan]📥 Confirmación recibida:[/bold cyan] '{user_input}'")

    # 2. Validación de pre-condiciones
    if not active_slots or not service_id:
        rprint("[yellow]⚠️ No hay slots activos o servicio seleccionado para confirmar.[/yellow]")
        return {
            "messages": [AIMessage(content="No tengo una reserva pendiente para confirmar. ¿Deseas ver nuestro catálogo de servicios?")],
            "next_action": "CATALOG"
        }

    selected_slot = None

    # --- LÓGICA DE DETECCIÓN (Híbrida: Hora o Índice) ---

    # A. Intento por hora exacta (Ej: "12:00" o "12.00")
    normalized_input = user_input.replace(".", ":")
    for slot in active_slots:
        # Buscamos si la hora (ej: "12:00") está contenida en lo que escribió el usuario
        if slot.get("time") and slot["time"] in normalized_input:
            selected_slot = slot
            rprint(f"[green]✅ Match por hora exacta:[/green] {slot['time']}")
            break

    # B. Intento por índice (Ej: "la 2", "el 1", "2")
    if not selected_slot:
        match = re.search(r'\b([1-9])\b', user_input)
        if match:
            idx = int(match.group(1)) - 1
            if 0 <= idx < len(active_slots):
                selected_slot = active_slots[idx]
                rprint(f"[green]✅ Match por índice:[/green] Opción {idx + 1}")

    # 3. Si no se pudo identificar el slot
    if not selected_slot:
        return {
            "messages": [AIMessage(content="No entendí tu elección. ¿Podrías decirme el número de la opción o la hora exacta?")],
            "next_action": "FINISH"
        }

    # 4. Persistencia: Llamada a la herramienta de reserva
    try:
        rprint(f"[bold blue]🚀 Intentando reservar ID {service_id} para {phone}...[/bold blue]")
        
        reserva = await book_appointment_tool(
            client_phone=phone,
            service_id=service_id,
            colab_id=selected_slot["collaborator_id"],
            dt_str=selected_slot["full_datetime"]
        )

        if reserva.get("success"):
            mensaje_final = reserva.get("message")
            rprint("[bold green]🎉 Cita confirmada exitosamente.[/bold green]")
        else:
            mensaje_final = "❌ Lo siento, hubo un problema al confirmar tu cita. Es posible que el horario ya no esté disponible."
            rprint("[bold red]❌ Error en la reserva de DB.[/bold red]")

    except Exception as e:
        logger.error(f"Error crítico en confirmation_node: {e}")
        mensaje_final = "Hubo un error técnico al procesar tu cita. Por favor, intenta de nuevo en unos minutos."

    # 5. SRP: Limpieza del estado para evitar colisiones en futuras interacciones
    return {
        "messages": [AIMessage(content=mensaje_final)],
        "active_slots": [],            # Limpiamos slots
        "selected_service_id": None,   # Limpiamos servicio
        "shown_service_ids": [],       # Limpiamos catálogo previo
        "next_action": "FINISH"
    }