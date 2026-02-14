from langgraph.graph import StateGraph, END
from app.agents.agent_state import AgentState
from app.agents.identity.nodes.greeting_node import greeting_node
from app.agents.identity.nodes.extractor_node import extractor_node

def create_valeria_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("extractor", extractor_node)
    workflow.add_node("greeting", greeting_node)

    # Flujo: Siempre intentamos extraer primero, luego saludamos
    workflow.set_entry_point("extractor")
    workflow.add_edge("extractor", "greeting")
    workflow.add_edge("greeting", END)

    return workflow.compile()