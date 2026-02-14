"""
Graph Builder — Dominio: Appointments
Flujo: extractor → confirmation → END
"""

from langgraph.graph import StateGraph, END
from app.agents.appointments.nodes.extractor_node import extractor_node
from app.agents.appointments.nodes.confirmation_node import confirmation_node


def create_appointments_graph(db):
    workflow = StateGraph(dict)

    workflow.add_node("extractor",    extractor_node)
    workflow.add_node("confirmation", lambda state: confirmation_node(state, db))

    workflow.set_entry_point("extractor")
    workflow.add_edge("extractor",    "confirmation")
    workflow.add_edge("confirmation", END)

    return workflow.compile()