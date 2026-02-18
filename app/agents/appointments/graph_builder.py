"""
Graph Builder — Dominio: Appointments
Flujo: confirmation → END (SRP aplicado) [cite: 2026-02-13]
"""

from langgraph.graph import StateGraph, END
# Eliminamos el extractor redundante para evitar duplicar trazas y costos [cite: 2026-02-13, 2026-02-18]
from app.agents.appointments.nodes.confirmation_node import confirmation_node

def create_appointments_graph(db):
    # Usamos dict o tu AgentState tipado para mantener consistencia física [cite: 2026-02-07]
    workflow = StateGraph(dict)

    # El nodo de confirmación ahora es el único responsable de persistir la cita en NEON [cite: 2026-02-18]
    workflow.add_node("confirmation", lambda state: confirmation_node(state, db))

    # El punto de entrada es directo; el Master ya hizo el trabajo sucio [cite: 2026-02-13]
    workflow.set_entry_point("confirmation")
    workflow.add_edge("confirmation", END)

    return workflow.compile()