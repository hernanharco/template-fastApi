import os
from openai import OpenAI
from dotenv import load_dotenv
from app.agents.agent_state import AgentState

load_dotenv()

client_ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def greeting_node(state: AgentState):
    name     = state.get("client_name")
    messages = state.get("messages", [])
    
    # Identificar si es una conversación en curso
    is_ongoing = len(messages) > 2

    if is_ongoing:
        system_prompt = (
            f"Eres Valeria de 'Beauty Pro'. Estás conversando con {name if name else 'el cliente'}. "
            "Responde de forma natural y breve al último mensaje.\n\n"
            "REGLAS DE RESPUESTA:\n"
            "1. DESPEDIDAS: Si el usuario se despide (chao, gracias, adiós, nos vemos), "
            "responde amablemente cerrando la conversación (ej: '¡A ti! Que tengas un lindo día').\n"
            "2. DISPONIBILIDAD: Solo si el usuario pregunta por horarios o disponibilidad, responde: "
            "'Dime qué día te viene bien y lo consulto para ti.'\n"
            "3. RESTRICCIONES: NUNCA inventes horas, fechas ni confirmes citas. "
            "Mantén la respuesta en menos de 20 palabras."
        )
    elif name:
        system_prompt = (
            f"Eres Valeria de 'Beauty Pro'. Saluda cálidamente a {name} por su nombre "
            "y dale la bienvenida de nuevo. Solo saluda."
        )
    else:
        system_prompt = (
            "Eres Valeria de 'Beauty Pro'. Saluda amablemente y pide el nombre del cliente. "
            "Solo saluda y pide el nombre."
        )

    response = client_ai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}] + messages,
        temperature=0.7 # Subimos un poco la temperatura para que no sea un robot repetitivo
    )

    return {
        "messages": [{"role": "assistant", "content": response.choices[0].message.content}],
        "current_node": "GREETING"
    }