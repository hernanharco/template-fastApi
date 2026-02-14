from langgraph.graph import StateGraph, END
from .nodes.extractor_node import extractor_node
from .nodes.availability_node import availability_node
from .state import BookingState  # ✅

def create_booking_graph(db):
    workflow = StateGraph(BookingState)  # ✅ schema tipado

    workflow.add_node("extractor", extractor_node)
    workflow.add_node("availability", lambda state: availability_node(state, db))

    workflow.set_entry_point("extractor")
    workflow.add_edge("extractor", "availability")
    workflow.add_edge("availability", END)

    return workflow.compile()