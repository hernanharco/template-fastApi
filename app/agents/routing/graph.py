import logging
from langgraph.graph import StateGraph, START, END

from app.agents.routing.state import RoutingState

from app.agents.nodes.customer_lookup_node import customer_lookup_node
from app.agents.nodes.router_node import router_node
from app.agents.nodes.greeting_node import greeting_node
from app.agents.nodes.catalog_node import catalog_node
from app.agents.nodes.booking_node import booking_node
from app.agents.nodes.confirmation_node import confirmation_node


logger = logging.getLogger(__name__)

workflow = StateGraph(RoutingState)

workflow.add_node("customer_lookup", customer_lookup_node)
workflow.add_node("router", router_node)
workflow.add_node("greeting", greeting_node)
workflow.add_node("catalog", catalog_node)
workflow.add_node("booking", booking_node)
workflow.add_node("confirmation", confirmation_node)


def greeting_next_step(state: RoutingState) -> str:
    current_name = state.get("client_name")

    if state.get("force_greeting"):
        return "CATALOG"

    if not current_name or current_name == "Nuevo Cliente" or state.get("wait_for_name"):
        return "WAIT"

    return "CATALOG"


workflow.add_edge(START, "customer_lookup")
workflow.add_edge("customer_lookup", "router")

workflow.add_conditional_edges(
    "router",
    lambda state: state.get("intent").value if state.get("intent") else None,
    {
        "GREETING": "greeting",
        "CATALOG": "catalog",
        "BOOKING": "booking",
        "CONFIRMATION": "confirmation",
        "FINISH": END,
    },
)

workflow.add_conditional_edges(
    "greeting",
    greeting_next_step,
    {
        "WAIT": END,
        "CATALOG": "catalog",
    },
)

workflow.add_conditional_edges(
    "catalog",
    lambda state: state.get("intent").value if state.get("intent") else None,
    {
        "BOOKING": "booking",
        "FINISH": END,
    },
)

workflow.add_conditional_edges(
    "booking",
    lambda state: state.get("intent").value if state.get("intent") else None,
    {
        "CONFIRMATION": END,
        "CATALOG": "catalog",
        "FINISH": END,
    },
)

workflow.add_edge("confirmation", END)

graph = workflow.compile()

logger.info("Maria Router Graph initialized successfully")