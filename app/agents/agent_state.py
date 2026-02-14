# app/agents/agent_state.py
from typing import TypedDict, Annotated, List, Optional
import operator

class AgentState(TypedDict):
    # 'operator.add' permite que los mensajes se acumulen sin borrar los anteriores
    messages: Annotated[List[dict], operator.add]
    date: Optional[str]
    client_name: Optional[str]
    time: Optional[str]
    service: Optional[str]
    current_node: str