# ¿Qué datos necesita este dominio? (ej: fecha, hora)
# 1. El Estado (State)
# En el video, la información "vuela" en variables. En LangGraph, hay un objeto único (el State) que viaja por todo el grafo. Cada nodo recibe el estado, le añade algo y lo pasa al siguiente.

# Ejemplo: El nodo saludo recibe el estado vacío y le añade user_name: "Pepe".

from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class GreetingState(TypedDict):
    # 'add_messages' permite que LangGraph concatene los mensajes automáticamente
    messages: Annotated[list, add_messages]
    tenant_name: str  # Útil para que el saludo sea "Hola, bienvenido a [Nombre Empresa]"