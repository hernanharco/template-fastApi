# app/agents/core/maria_master.py
from typing import Annotated, Literal
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.orm import Session
from rich import print as rprint

# Imports de tus otros módulos
from app.agents.identity.identitynode import identity_node, AgentState
from app.agents.service.servicenode import service_expert_node
from app.models.clients import Client

# ==========================================
# PARTE 1: LÓGICA DEL GRAFO (Lo que me preguntaste)
# ==========================================

# app/agents/core/maria_master.py

def should_go_to_main(state: AgentState) -> Literal["service_expert", "identity", END]:
    # 1. Obtener el nombre y el historial
    nombre = state.get("client_name")
    messages = state.get("messages", [])
    
    # 2. Lógica de Salto Proactivo:
    # Si tenemos nombre Y el último mensaje es de la IA confirmando el registro...
    # (Ej: "¡Mucho gusto, Hernán! Ya te registré...")
    # Queremos que pase DIRECTO al experto de servicios en el mismo turno.
    if nombre and nombre != "Nuevo Cliente":
        # Si el último mensaje es del usuario, vamos a servicios.
        # Si el último mensaje es de la IA pero es el de "Ya te registré", 
        # forzamos una ejecución más hacia service_expert.
        if messages and isinstance(messages[-1], HumanMessage):
            return "service_expert"
        
        # Si el último mensaje fue la confirmación del nombre, saltamos a servicios
        # para que el usuario no tenga que escribir "hola" de nuevo.
        if "Ya te registré" in messages[-1].content:
            return "service_expert"

    # 3. Freno estándar: Si la IA ya habló y NO fue para registrar el nombre, terminamos.
    if messages and isinstance(messages[-1], AIMessage):
        return END

    # 4. Si no hay nombre, seguimos en identidad
    if not nombre or nombre == "Nuevo Cliente":
        return "identity"
    
    return "service_expert"

def main_assistant_node(state: AgentState) -> dict:
    return {
        "messages": [AIMessage(content="Estoy lista para ayudarte con tu cita 💇‍♀️")],
        "current_node": "main_assistant",
    }

def build_maria_master_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("identity", identity_node)
    workflow.add_node("service_expert", service_expert_node)
    workflow.add_node("main_assistant", main_assistant_node)

    workflow.add_edge(START, "identity")
    
    workflow.add_conditional_edges(
        "identity",
        should_go_to_main,
        {
            "service_expert": "service_expert",
            "identity": "identity",
            "main_assistant": "main_assistant",
            END: END,
        }
    )
    
    workflow.add_edge("service_expert", "identity")
    workflow.add_edge("main_assistant", "identity")

    return workflow.compile()

# Instancia del motor del grafo
graph_maria = build_maria_master_graph()


# ==========================================
# PARTE 2: EL ORQUESTADOR (La clase MariaMaster)
# ==========================================

class MariaMaster:
    """
    Esta clase es la que invoca al 'graph_maria' de arriba.
    """
    def process(self, db: Session, phone: str, user_input: str) -> str:
        rprint(f"\n[bold blue]─── 🧠 PROCESANDO: {phone} ───[/bold blue]")
        
        # 1. Neon: Buscar cliente
        client = db.query(Client).filter(Client.phone == phone).first()
        if not client:
            client = Client(phone=phone, full_name="Nuevo Cliente", business_id=1, metadata_json={"messages": []})
            db.add(client)
            db.commit()
            db.refresh(client)

        # 2. Hidratar mensajes
        history = []
        for m in client.metadata_json.get("messages", []):
            if m["role"] == "user":
                history.append(HumanMessage(content=m["content"]))
            else:
                history.append(AIMessage(content=m["content"]))

        # 3. Preparar inputs para el grafo 'graph_maria'
        nombre_actual = client.full_name if client.full_name != "Nuevo Cliente" else None
        inputs = {
            "messages": history + [HumanMessage(content=user_input)],
            "client_phone": phone,
            "client_name": nombre_actual,
            "business_slug": "la-mega-tienda"
        }

        # 4. LANZAR EL GRAFO
        rprint("[magenta]🚀 Entrando al Grafo...[/magenta]")
        final_state = graph_maria.invoke(inputs, config={"configurable": {"thread_id": phone}})

        # 5. Guardar resultados en Neon
        if final_state.get("client_name") and final_state["client_name"] != "Nuevo Cliente":
            client.full_name = final_state["client_name"]

        updated_msgs = []
        for m in final_state["messages"]:
            role = "user" if isinstance(m, HumanMessage) else "assistant"
            updated_msgs.append({"role": role, "content": m.content})
        
        client.metadata_json = {"messages": updated_msgs}
        db.commit()

        # 6. Devolver respuesta final
        return final_state["messages"][-1].content

# La instancia que usa el test_agent.py
maria = MariaMaster()