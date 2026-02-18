from langgraph.graph import StateGraph, END
from app.agents.agent_state import AgentState
from app.agents.identity.nodes.greeting_node import greeting_node
# Eliminamos la importación del extractor local [cite: 2026-02-13]

def create_valeria_graph():
    """
    SRP: Este grafo solo se encarga de la interacción inicial y saludo.
    Ya NO extrae información porque el Master Extractor ya lo hizo. [cite: 2026-02-13]
    """
    workflow = StateGraph(AgentState)

    # 1. Mantenemos solo el nodo de saludo (greeting)
    workflow.add_node("greeting", greeting_node)

    # 2. El punto de entrada es directamente el saludo
    # Usamos los datos (nombre, etc.) que el Master ya guardó en Neon [cite: 2026-02-18]
    workflow.set_entry_point("greeting")
    workflow.add_edge("greeting", END)

    return workflow.compile()