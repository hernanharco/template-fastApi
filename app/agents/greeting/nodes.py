# app/agents/greeting/nodes.py
from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.agents.routing.state import RoutingState


async def greeting_node(state: RoutingState):
    """
    SRP: Su única responsabilidad es generar un saludo humano y empático.
    """
    llm = ChatOpenAI(model="gpt-4o-mini", api_key=settings.OPENAI_API_KEY)

    # Obtenemos los datos del estado
    raw_name = state.get("client_name", "Nuevo Cliente")
    is_new = state.get("is_new_user", False)
    name_rejected = state.get("name_rejected", False)
    last_message = state["messages"][-1].content

    # Limpiamos el nombre para el prompt: si es "Nuevo Cliente", lo tratamos como vacío
    display_name = "" if raw_name == "Nuevo Cliente" else raw_name

    # --- LÓGICA DE INSTRUCCIONES (Priorizando casos) ---

    if name_rejected:
        # Caso A: El usuario intentó bromear o puso algo inválido
        instruction = (
            f"El usuario dijo '{last_message}', lo cual no parece un nombre real. "
            "No le sigas el juego con ese nombre falso. Dile con humor que necesitas "
            "su nombre de pila real para poder gestionar su cita en el sistema."
        )
    elif is_new and not display_name:
        # Caso B: Usuario nuevo que aún no nos ha dicho quién es
        instruction = (
            "Es la primera vez que este usuario escribe. Saluda calurosamente, "
            "preséntate como María y pídele amablemente su nombre para registrarlo."
        )
    elif is_new and display_name:
        # Caso C: Usuario nuevo que ACABA de darnos su nombre válido
        instruction = (
            f"El usuario acaba de decir que se llama '{display_name}'. "
            "Dale la bienvenida oficial, confirma que ya lo registraste y "
            "pregúntale en qué servicio está interesado hoy."
        )
    else:
        # Caso D: Cliente antiguo que ya conocemos
        instruction = (
            f"Saluda a '{display_name}', es un cliente recurrente. "
            "Sé amable, directa y pregúntale cómo puedes ayudarle hoy."
        )

    # --- CONFIGURACIÓN DEL SISTEMA ---
    system_message = (
        f"Eres {settings.NAME_IA}, la asistente virtual de {settings.BUSINESS_NAME}. "
        "Tu tono es amigable, profesional y cercano. NUNCA uses malas palabras. "
        "REGLA DE ORO: Jamás menciones el término 'Nuevo Cliente'. Si no tienes un nombre, "
        "usa vocativos genéricos amables como 'amigo' o simplemente no uses nombre.\n"
        f"INSTRUCCIÓN ESPECÍFICA: {instruction}"
    )

    # Invocamos al LLM con manejo de errores
    try:
        response = await llm.ainvoke(
            [("system", system_message), ("user", last_message)]
        )
    except Exception as e:
        logger.error(f"Error en LLM greeting_node: {e}")
        # Fallback: mensaje genérico pero seguro
        MockResponse = type('MockResponse', (), {'content': f"¡Hola! Soy {settings.NAME_IA}. ¿En qué puedo ayudarte hoy?"})
        response = MockResponse()

    return {
        "messages": [response],
        # Mantenemos los flags para que el grafo decida el siguiente paso
        "client_name": state.get("client_name"),
        "name_rejected": state.get("name_rejected"),
    }
