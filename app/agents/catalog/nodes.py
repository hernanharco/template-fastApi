import json
import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from app.core.config import settings
from app.agents.routing.state import RoutingState
from app.agents.catalog.tools import get_services_catalog

logger = logging.getLogger(__name__)

async def catalog_node(state: RoutingState):
    """
    🎯 SRP: Única responsabilidad: Gestionar la selección o exhibición del catálogo.
    Muestra una vista Premium minimalista sin precios ni tiempos.
    """
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
    )

    user_input = state["messages"][-1].content
    
    # 1. Consulta de datos (Infraestructura mínima, valor máximo)
    services_data = get_services_catalog()
    if not services_data:
        return {
            "messages": [AIMessage(content="En este momento estamos preparando nuevas experiencias para ti. Vuelve pronto.")],
            "next_action": "FINISH"
        }

    # 2. Identificación de intención mediante LLM
    system_prompt = (
        f"Eres el concierge de {settings.BUSINESS_NAME}.\n"
        "Tu misión es identificar si el cliente ha seleccionado un servicio específico.\n"
        f"CATÁLOGO DISPONIBLE: {json.dumps(services_data)}\n"
        "REGLA: Si el cliente menciona un servicio o su número, devuelve el ID. Si es un saludo o consulta general, null."
    )

    json_format = {
        "identified_service_id": "int o null",
        "reason": "str"
    }

    try:
        response = await llm.ainvoke([
            ("system", f"{system_prompt}\nResponde en JSON: {json.dumps(json_format)}"),
            ("user", user_input),
        ])
        
        data = json.loads(response.content.replace("```json", "").replace("```", "").strip())
    except Exception as e:
        logger.error(f"Error en catalog_node: {e}")
        return {"next_action": "FINISH"}

    service_id = data.get("identified_service_id")

    # CASO A: Selección detectada (Manda al flujo de reserva)
    if service_id:
        return {
            "next_action": "BOOKING",
            "selected_service_id": service_id,
        }

    # CASO B: Vista Premium (Limpia y sofisticada)
    # Diseño: Usamos viñetas elegantes y eliminamos datos técnicos (precios/minutos)
    texto_premium = (
        f"✨ *Bienvenido a {settings.BUSINESS_NAME}* ✨\n\n"
        "Es un placer asistirte. Hemos diseñado una selección de experiencias "
        "exclusivas para tu cuidado:\n\n"
    )

    for s in services_data:
        # Solo mostramos el nombre del servicio con un estilo limpio
        texto_premium += f"◦  _{s['name']}_\n"

    texto_premium += "\n¿Cuál de ellas te gustaría disfrutar hoy?"

    return {
        "messages": [AIMessage(content=texto_premium)],
        "next_action": "FINISH", # 🛑 Se detiene para que el usuario responda
        "shown_service_ids": [s['id'] for s in services_data]
    }