import logging
import random
from langchain_core.messages import AIMessage
from app.core.config import settings
from app.agents.routing.state import RoutingState
from app.agents.catalog.tools import get_services_catalog
from rich import print as rprint

logger = logging.getLogger(__name__)

async def catalog_node(state: RoutingState):
    """
    🎯 SRP: Única responsabilidad: Presentar el catálogo de servicios disponible
    y registrar qué IDs se le mostraron al usuario para el ruteo posterior.
    """
    # 1. Obtener datos de la DB (vía tool)
    services_data = get_services_catalog()

    if not services_data:
        rprint("[yellow]⚠️ No se encontraron servicios en la base de datos.[/yellow]")
        return {
            "messages": [AIMessage(content="✨ *Estamos preparando nuevas experiencias para ti. Vuelve pronto.*")],
            "next_action": "FINISH"
        }

    # 2. Configuración estética (Emojis cambiantes para no ser monótonos)
    iconos = ["✂️", "✨", "💅", "💈", "🌟", "💆‍♀️", "🔥", "💎"]
    
    # 3. Construcción del mensaje con formato limpio (Negritas en lugar de cursivas)
    header = f"✨ *Bienvenido a {settings.BUSINESS_NAME}* ✨\n\n"
    body = "He diseñado una selección de experiencias exclusivas para ti:\n\n"
    
    for i, s in enumerate(services_data, 1):
        # Seleccionamos un emoji aleatorio para cada item
        emoji = random.choice(iconos)
        # Usamos negritas para el nombre del servicio para mejor legibilidad
        body += f"{i}. {emoji} *{s['name']}*\n"

    footer = (
        "\n━━━━━━━━━━━━━━\n"
        "👉 *¿Cuál de ellas te gustaría disfrutar hoy?*\n"
        "_(Escribe el nombre o el número de la opción)_"
    )

    full_message = header + body + footer

    # 4. Registro de IDs mostrados
    # Esto es VITAL para que el router sepa que si el usuario dice "1", 
    # se refiere al primer ID de esta lista específica.
    shown_ids = [s['id'] for s in services_data]

    rprint(f"[green]📱 Catálogo desplegado con {len(shown_ids)} servicios.[/green]")

    return {
        "messages": [AIMessage(content=full_message)],
        "shown_service_ids": shown_ids,
        "next_action": "FINISH"
    }