from langgraph.graph import StateGraph, END
# Eliminamos la importación del extractor_node redundante [cite: 2026-02-13]
from .nodes.availability_node import availability_node
from app.agents.agent_state import AgentState

def create_booking_graph(db):
    """
    SRP: Este grafo solo se encarga de la lógica de reserva, 
    ya NO extrae información del lenguaje natural. [cite: 2026-02-13]
    """
    workflow = StateGraph(AgentState)

    # 1. Definimos el nodo de disponibilidad
    # Ahora es el primer y único punto de decisión técnica [cite: 2026-02-13]
    workflow.add_node("availability", lambda state: availability_node(state, db))

    # 2. El punto de entrada es directamente la búsqueda de huecos [cite: 2026-02-13]
    # Ya no pasamos por 'extractor' porque el Master ya llenó el state [cite: 2026-02-18]
    workflow.set_entry_point("availability")
    
    # 3. Del resultado de disponibilidad vamos al final
    workflow.add_edge("availability", END)

    return workflow.compile()