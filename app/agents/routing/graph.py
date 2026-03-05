import os
import logging
from langgraph.graph import StateGraph, START, END
from app.agents.routing.state import RoutingState

# 1. DOMINIO ROUTING (Enrutamiento e Identificación)
from app.agents.routing.nodes import router_node, customer_lookup_node

# 2. DOMINIO GREETING (Social)
from app.agents.greeting.nodes import greeting_node

# 3. DOMINIO CATALOG (Exhibición)
from app.agents.catalog.nodes import catalog_node

# 4. DOMINIO BOOKING (Negociación de Disponibilidad)
from app.agents.booking.nodes import booking_node

# 5. DOMINIO APPOINTMENTS (Transaccional)
from app.agents.appointments.nodes import confirmation_node

logger = logging.getLogger(__name__)

# ==========================================
# CONFIGURACIÓN DEL GRAFO
# ==========================================
workflow = StateGraph(RoutingState)

# Registro de Nodos (SRP: Cada nodo tiene una responsabilidad clara)
workflow.add_node("customer_lookup", customer_lookup_node)
workflow.add_node("router", router_node)
workflow.add_node("greeting", greeting_node)
workflow.add_node("catalog", catalog_node)
workflow.add_node("booking", booking_node)
workflow.add_node("appointments", confirmation_node)

def check_greeting_next_step(state: RoutingState) -> str:
    """
    🎯 LÓGICA DE FLUJO CONTINUO:
    Decide si el flujo se detiene (END) para esperar respuesta del usuario 
    o si avanza automáticamente al catálogo (catalog).
    """
    current_name = state.get("client_name", "Nuevo Cliente")
    
    # 1. Si es un cliente nuevo o estamos forzando la petición de nombre, detenemos la ejecución.
    if current_name == "Nuevo Cliente" or state.get("wait_for_name"):
        return "wait_for_name"

    # 2. 🚀 SALTO AUTOMÁTICO: Si ya conocemos al cliente, saludamos y
    # pasamos inmediatamente al catálogo sin que el usuario tenga que escribir nada.
    return "show_catalog"

# ==========================================
# LÓGICA DE FLUJO (ARISTAS)
# ==========================================

# Flujo de Inicio
workflow.add_edge(START, "customer_lookup")
workflow.add_edge("customer_lookup", "router")

# 1. EL ROUTER: Decisor de intenciones iniciales
workflow.add_conditional_edges(
    "router",
    lambda state: state["next_action"],
    {
        "GREETING": "greeting",
        "CATALOG": "catalog",
        "BOOKING": "booking",
        "CONFIRMATION": "appointments",
        "FINISH": END,
    },
)

# 2. SALIDA DE GREETING (Encadenamiento Dinámico)
workflow.add_conditional_edges(
    "greeting",
    check_greeting_next_step,
    {
        "wait_for_name": END,        # Se detiene si hay que pedir nombre (Cliente Nuevo)
        "show_catalog": "catalog",   # Salta directo a catálogo (Cliente Existente)
    },
)

# 3. SALIDA DE CATALOG
workflow.add_conditional_edges(
    "catalog",
    lambda state: state.get("next_action"),
    {
        "FINISH": END,               # Se detiene tras mostrar los servicios
        "BOOKING": "booking",
        "GREETING": END,             # Protección anti-bucle
    },
)

# 4. SALIDA DE BOOKING
workflow.add_conditional_edges(
    "booking",
    lambda state: state.get("next_action"),
    {
        "CONFIRM": "appointments",
        "CONFIRMATION": "appointments",
        "FINISH": END,
        "CATALOG": "catalog",
    },
)

# 5. SALIDA DE APPOINTMENTS
workflow.add_edge("appointments", END)

# Compilación final
graph = workflow.compile()