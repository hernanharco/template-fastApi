import json
from openai import OpenAI
from app.agents.agent_state import AgentState

client_ai = OpenAI()

def extractor_node(state: AgentState):
    current_name = state.get("client_name")
    user_msg = state["messages"][-1]["content"]

    # CAMBIO 1: Solo saltar si ya tenemos un nombre REAL (que no sea Usuario)
    if current_name and current_name.lower() not in ["usuario", "cliente", "none"]:
        return {}

    # CAMBIO 2: Prompt agresivo para nombres cortos como "Ian"
    prompt = """
    Eres un experto en identificar nombres de personas en chats de belleza.
    TAREA: Extrae el nombre del usuario del mensaje.
    
    REGLAS ORO:
    1. Si el mensaje es una sola palabra (ej: 'Ian', 'ana', 'pedro'), ASUME que es su nombre.
    2. Si el mensaje es 'me llamo X' o 'soy X', extrae X.
    3. Ignora saludos como 'hola' o 'buenos dias'.
    4. Responde estrictamente en JSON: {"name": "Nombre"} o {"name": null} si es solo un saludo.
    """
    
    response = client_ai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_msg}
        ],
        response_format={"type": "json_object"}
    )
    
    data = json.loads(response.choices[0].message.content)
    extracted = data.get("name")
    
    # CAMBIO 3: Si la IA falla pero es una sola palabra, la rescatamos nosotros (Heurística)
    words = user_msg.strip().split()
    if not extracted and len(words) == 1 and words[0].lower() not in ["hola", "buenas"]:
        extracted = words[0].capitalize()

    return {"client_name": extracted}