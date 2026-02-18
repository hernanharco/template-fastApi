# app/agents/service/graph_builder.py
from langgraph.graph import StateGraph, END
from app.agents.agent_state import AgentState
# Eliminamos el service_extractor_node redundante
from app.agents.service.nodes.service_node import service_validator_node

def create_service_graph(db):
    """
    SRP: Este grafo solo valida si el servicio existe en la base de datos física.
    La extracción de lenguaje natural ya ocurrió en el Master.
    """
    workflow = StateGraph(AgentState)

    # El nodo validador recibe el estado que el Master ya llenó con 'service_type'
    workflow.add_node("validator", lambda state: service_validator_node(db, state))

    # El flujo es directo y ultra rápido
    workflow.set_entry_point("validator")
    workflow.add_edge("validator", END)

    return workflow.compile()