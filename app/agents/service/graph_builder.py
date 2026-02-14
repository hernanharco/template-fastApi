# app/agents/service/graph_builder.py
from langgraph.graph import StateGraph, END
from app.agents.agent_state import AgentState
from app.agents.service.nodes.extractor_node import service_extractor_node
from app.agents.service.nodes.service_node import service_validator_node

def create_service_graph(db):
    workflow = StateGraph(AgentState)

    # AQUÍ ESTÁ EL CAMBIO: Inyectamos 'db' y 'state' correctamente [cite: 2026-02-07]
    workflow.add_node("extractor", lambda state: service_extractor_node(db, state))
    
    # Hacemos lo mismo con el validador por consistencia [cite: 2026-02-13]
    workflow.add_node("validator", lambda state: service_validator_node(db, state))

    # El resto se mantiene igual
    workflow.set_entry_point("extractor")
    workflow.add_edge("extractor", "validator")
    workflow.add_edge("validator", END)

    return workflow.compile()