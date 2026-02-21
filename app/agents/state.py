# app/agents/state.py
from typing import TypedDict, Optional, Literal, Annotated
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    # Annotated permite que los mensajes se sumen a la lista en lugar de sobrescribirse
    messages: Annotated[list[BaseMessage], operator.add]
    client_name: Optional[str]
    client_phone: Optional[str]
    business_slug: str
    last_updated: Optional[str]
    current_node: Optional[Literal["identity", "service_expert", "main_assistant"]]