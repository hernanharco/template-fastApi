import json
from openai import OpenAI
from app.agents.agent_state import AgentState

client_ai = OpenAI()

def extractor_node(state: AgentState):
    # Solo intentamos extraer el nombre si no lo conocemos ya
    if state.get("client_name"):
        return {}

    prompt = """
    Analiza el mensaje y extrae el nombre del usuario si se está presentando.
    Responde estrictamente en JSON: {"name": "Nombre" o null}
    """
    
    response = client_ai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": state["messages"][-1]["content"]}
        ],
        response_format={"type": "json_object"}
    )
    
    data = json.loads(response.choices[0].message.content)
    return {"client_name": data.get("name")}