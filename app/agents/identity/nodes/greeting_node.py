import os
from openai import OpenAI
from dotenv import load_dotenv
from app.agents.agent_state import AgentState

load_dotenv()

client_ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def greeting_node(state: AgentState):
    # Extraemos datos del estado
    name = state.get("client_name")
    messages = state.get("messages", [])
    
    # 1. OBTENER EL ÚLTIMO MENSAJE (Sin errores de nombre de variable)
    last_message = messages[-1]["content"].lower() if messages else ""
    
    # 2. DETECCIÓN DE DESPEDIDAS
    despedidas = ["gracias", "adios", "chao", "nos vemos", "bye", "hasta luego", "vale", "perfecto", "mil gracias"]
    es_despedida = any(palabra in last_message for palabra in despedidas)

    # 3. SELECCIÓN DE LÓGICA SEGÚN EL CONTEXTO
    if es_despedida:
        # El usuario se está yendo o agradeciendo
        system_prompt = (
            f"Eres Valeria de 'Beauty Pro'. El cliente {name if name else ''} se está despidiendo. "
            "Responde con una despedida muy breve, dulce y profesional. "
            "NO le des la bienvenida de nuevo ni hagas preguntas. Solo cierra la charla."
        )
    
    elif name and name.lower() != "usuario":
        # Ya conocemos al cliente
        if len(messages) > 2:
            # Es una conversación fluida, ya pasamos el saludo inicial
            system_prompt = (
                f"Eres Valeria de 'Beauty Pro'. Estás conversando con {name}. "
                "Responde de forma natural, muy breve (menos de 20 palabras). "
                "No repitas saludos de bienvenida. Si el cliente no pregunta nada específico, "
                "solo sé amable y mantente a disposición."
            )
        else:
            # Es el primer mensaje pero ya sabemos su nombre de la base de datos
            system_prompt = (
                f"Eres Valeria de 'Beauty Pro'. Saluda cálidamente a {name} por su nombre. "
                "Dile que es un gusto volver a verle y pregúntale en qué puedes ayudarle hoy."
            )
    else:
        # No conocemos el nombre, es un cliente nuevo o desconocido
        system_prompt = (
            "Eres Valeria de 'Beauty Pro'. Saluda amablemente y pide el nombre del cliente. "
            "Explícale que te gustaría saber su nombre para poder atenderle mejor y agendar sus citas."
        )

    # 4. LLAMADA A LA IA
    response = client_ai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}] + messages,
        temperature=0.7 
    )

    # 5. RETORNO DEL ESTADO ACTUALIZADO
    return {
        "messages": [{"role": "assistant", "content": response.choices[0].message.content}],
        "current_node": "GREETING"
    }