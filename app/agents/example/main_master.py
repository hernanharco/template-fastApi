from datetime import datetime
from typing import Annotated, TypedDict, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from app.agents.tools import InventoryService

# 1. Estado extendido con Seguimiento de Tiempo
class AgentState(TypedDict):
    """Estado del agente con memoria temporal."""
    messages: Annotated[list, add_messages]
    # Campo para medir latencia o tiempo entre turnos
    last_updated: Optional[str] 

class CoreAppointmentAgent:
    def __init__(self, model_name: str = "gpt-4o"):
        self.tools = [InventoryService.multiply, InventoryService.get_categories]
        self.model = ChatOpenAI(model=model_name, temperature=0).bind_tools(self.tools)
        self.tool_node = ToolNode(self.tools)

    def _sync_memory(self, state: AgentState):
        """
        Nodo de utilidad: Actualiza el timestamp de la última interacción.
        Esto permite calcular si una sesión ha expirado o cuánto tardó el usuario.
        """
        now = datetime.now().isoformat()
        return {"last_updated": now}

    def _call_model(self, state: AgentState):
        # Aquí podrías usar state["last_updated"] para darle contexto al LLM
        # Ej: "Veo que tardaste 2 días en responder..."
        response = self.model.invoke(state["messages"])
        return {"messages": [response]}

    def compile_graph(self):
        workflow = StateGraph(AgentState)

        # Agregamos el nodo de sincronización
        workflow.add_node("sync_memory", self._sync_memory)
        workflow.add_node("assistant", self._call_model)
        workflow.add_node("tools", self.tool_node)

        # Flujo: START -> Sync -> Assistant
        workflow.add_edge(START, "sync_memory")
        workflow.add_edge("sync_memory", "assistant")
        
        workflow.add_conditional_edges("assistant", tools_condition)
        workflow.add_edge("tools", "assistant")

        return workflow.compile()

# Instancia para LangGraph CLI
agent_executor = CoreAppointmentAgent()
graph_maria = agent_executor.compile_graph()