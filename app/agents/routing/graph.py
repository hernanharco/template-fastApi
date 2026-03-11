import logging
from langgraph.graph import StateGraph, START, END

from app.agents.routing.state import RoutingState

from app.agents.nodes.customer_lookup_node import customer_lookup_node
from app.agents.nodes.router_node import router_node
from app.agents.nodes.greeting_node import greeting_node
from app.agents.nodes.catalog_node import catalog_node
from app.agents.nodes.booking_node import booking_node
from app.agents.nodes.confirmation_node import confirmation_node
from app.agents.nodes.finish_node import finish_node
from app.agents.nodes.time_parser_node import time_parser_node
from app.agents.nodes.time_filter_node import time_filter_node
from app.agents.nodes.favorite_fallback_node import favorite_fallback_node


logger = logging.getLogger(__name__)

workflow = StateGraph(RoutingState)

# ── Nodos ─────────────────────────────────────────────────────────────────────

workflow.add_node("customer_lookup",   customer_lookup_node)
workflow.add_node("router",            router_node)
workflow.add_node("greeting",          greeting_node)
workflow.add_node("catalog",           catalog_node)
workflow.add_node("booking",           booking_node)
workflow.add_node("confirmation",      confirmation_node)
workflow.add_node("finish",            finish_node)
workflow.add_node("time_parser",       time_parser_node)
workflow.add_node("time_filter",       time_filter_node)
workflow.add_node("favorite_fallback", favorite_fallback_node)


# ── Helpers de routing ────────────────────────────────────────────────────────

def _intent(state: RoutingState) -> str:
    return state.get("intent").value if state.get("intent") else "FINISH"


def greeting_next_step(state: RoutingState) -> str:
    if state.get("force_greeting"):
        return "CATALOG"
    current_name = state.get("client_name")
    if not current_name or current_name == "Nuevo Cliente" or state.get("wait_for_name"):
        return "WAIT"
    return "CATALOG"


# ── Edges ─────────────────────────────────────────────────────────────────────

workflow.add_edge(START, "customer_lookup")
workflow.add_edge("customer_lookup", "router")

workflow.add_conditional_edges(
    "router",
    _intent,
    {
        "GREETING":     "greeting",
        "CATALOG":      "catalog",
        "BOOKING":      "booking",
        "CONFIRMATION": "confirmation",
        "TIME_FILTER":  "time_filter",
        "TIME_PARSER":  "time_parser",
        "FINISH":       END,
    },
)

workflow.add_conditional_edges(
    "greeting",
    greeting_next_step,
    {
        "WAIT":    END,
        "CATALOG": "catalog",
    },
)

workflow.add_conditional_edges(
    "catalog",
    _intent,
    {
        "BOOKING": "booking",
        "FINISH":  END,
    },
)

workflow.add_conditional_edges(
    "booking",
    _intent,
    {
        "FAVORITE_FALLBACK": "favorite_fallback",
        "CONFIRMATION":      END,
        "CATALOG":           "catalog",
        "FINISH":            END,
    },
)

workflow.add_conditional_edges(          # ← único cambio respecto a tu versión
    "favorite_fallback",
    _intent,
    {
        "CONFIRMATION": END,   # muestra el mensaje y espera respuesta del usuario
        "FINISH":       END,   # sin opciones disponibles
    },
)

workflow.add_conditional_edges(
    "confirmation",
    _intent,
    {
        "BOOKING":      "booking",
        "TIME_FILTER":  "time_filter",
        "CONFIRMATION": END,
        "FINISH":       "finish",
    },
)

workflow.add_edge("finish", END)

workflow.add_conditional_edges(
    "time_filter",
    _intent,
    {
        "BOOKING":      "booking",
        "CONFIRMATION": END,
    },
)

workflow.add_conditional_edges(
    "time_parser",
    _intent,
    {
        "BOOKING":      "booking",
        "CONFIRMATION": END,
        "FINISH":       END,
    },
)

# ── Compilar ──────────────────────────────────────────────────────────────────

graph = workflow.compile()

logger.info("Maria Router Graph initialized successfully")