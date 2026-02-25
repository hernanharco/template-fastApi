from typing import Annotated, Literal
import re
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.orm import Session
from rich import print as rprint

from app.agents.identity.identitynode import identity_node, AgentState
from app.agents.service.servicenode import service_expert_node
from app.agents.booking.booking_node import booking_expert_node
from app.agents.appointments.appointments_node import appointment_confirmation_node
from app.models.clients import Client
from app.agents.core.extractor_master import extract_intent

# ==========================================
# PARTE 1: NODOS Y ROUTER
# ==========================================

def farewell_node(state: AgentState) -> dict:
    return {
        "messages": [AIMessage(content="¡De nada! Aquí estaré si necesitas algo más. ¡Que tengas un gran día! ✨")],
        "current_node": "farewell",
        "service_id": None
    }

def main_assistant_node(state: AgentState) -> dict:
    return {
        "messages": [AIMessage(content="Estoy lista para ayudarte con tu cita 💇‍♀️")],
        "current_node": "main_assistant",
    }

def should_go_to_main(state: AgentState) -> Literal["service_expert", "booking_expert", "appointment_confirmation", "farewell", "identity", END]:
    nombre = state.get("client_name")
    messages = state.get("messages", [])
    
    if not messages or isinstance(messages[-1], AIMessage): return END

    last_user_msg = messages[-1].content.lower().strip()
    if not nombre or nombre == "Nuevo Cliente": return "identity"
    
    history = messages[:-1][-5:] if len(messages) > 1 else []
    intent = extract_intent(last_user_msg, history)
    rprint(f"[bold magenta]🔮 IA ROUTER INTENT:[/bold magenta] {intent}")

    # REGLA DE ORO: Manejo del "si" tras un rechazo
    last_ai_msg = ""
    for m in reversed(messages[:-1]):
        if isinstance(m, AIMessage):
            last_ai_msg = m.content.lower()
            break

    if ("lo siento" in last_ai_msg or "no me quedan" in last_ai_msg) and intent == "confirmation":
        rprint("[bold yellow]🔄 ROUTER: El usuario aceptó buscar otro día. Volvemos a Booking.[/bold yellow]")
        return "booking_expert"

    if intent == "confirmation": return "appointment_confirmation"
    if intent == "booking": return "booking_expert"
    if intent in ["greeting", "info"]: return "service_expert"
    if intent == "farewell": return "farewell"

    return "service_expert"

# ==========================================
# PARTE 2: CONSTRUCCIÓN DEL GRAFO (DEFINICIÓN Y ASIGNACIÓN)
# ==========================================

def build_maria_master_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("identity", identity_node)
    workflow.add_node("service_expert", service_expert_node)
    workflow.add_node("booking_expert", booking_expert_node)
    workflow.add_node("appointment_confirmation", appointment_confirmation_node)
    workflow.add_node("main_assistant", main_assistant_node)
    workflow.add_node("farewell", farewell_node)

    workflow.add_edge(START, "identity")
    
    workflow.add_conditional_edges(
        "identity",
        should_go_to_main,
        {
            "service_expert": "service_expert",
            "booking_expert": "booking_expert",
            "appointment_confirmation": "appointment_confirmation",
            "farewell": "farewell",
            "identity": "identity",
            "main_assistant": "main_assistant",
            END: END,
        }
    )
    
    for node in ["service_expert", "booking_expert", "appointment_confirmation", "main_assistant", "farewell"]:
        workflow.add_edge(node, END)

    return workflow.compile()

# IMPORTANTE: Creamos la instancia del grafo ANTES de la clase que lo usa
graph_maria = build_maria_master_graph()

# ==========================================
# PARTE 3: EL ORQUESTADOR
# ==========================================

class MariaMaster:
    def process(self, db: Session, phone: str, user_input: str) -> dict:
        rprint(f"\n[bold blue]─── 🧠 PROCESANDO: {phone} ───[/bold blue]")
        
        # 1. Obtener cliente
        client = db.query(Client).filter(Client.phone == phone).first()
        if not client:
            client = Client(phone=phone, full_name="Nuevo Cliente", business_id=1, metadata_json={"messages": [], "service_id": None})
            db.add(client); db.commit(); db.refresh(client)

        # 2. Reconstruir historial de objetos de LangChain
        history = []
        history_raw = client.metadata_json.get("messages", [])
        for m in history_raw:
            role_class = HumanMessage if m["role"] == "user" else AIMessage
            history.append(role_class(content=m["content"]))

        # ✨ EL PARCHE DE CONTEXTO:
        # Creamos un string simple con los últimos 3-4 mensajes para que la IA del extractor tenga "memoria".
        # Esto es lo que usará extract_booking_intent(user_msg, history_text)
        context_string = "\n".join([f"{m['role']}: {m['content']}" for m in history_raw[-4:]])

        # 3. Preparar entrada para el grafo
        inputs = {
            "messages": history + [HumanMessage(content=user_input)],
            "client_phone": phone,
            "client_name": client.full_name if client.full_name != "Nuevo Cliente" else None,
            "business_slug": "la-mega-tienda",
            "service_id": client.metadata_json.get("service_id"),
            "history_text": context_string # 👈 Pasamos el contexto aquí
        }

        try:
            # 4. Ejecutar el Grafo
            final_state = graph_maria.invoke(inputs, config={"configurable": {"thread_id": phone}})
            
            # 5. Persistencia de nombre
            if final_state.get("client_name") and final_state["client_name"] != "Nuevo Cliente":
                client.full_name = final_state["client_name"]

            # 6. Guardar mensajes y service_id (Persistencia en Neon)
            updated_msgs = [{"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": m.content} for m in final_state["messages"]]
            client.metadata_json = {
                "messages": updated_msgs, 
                "service_id": final_state.get("service_id")
            }
            db.commit()

            return {
                "text": final_state["messages"][-1].content,
                "has_changes": (final_state.get("current_node") == "appointment_confirmation")
            }
        except Exception as e:
            rprint(f"[bold red]❌ ERROR EN EL GRAFO:[/bold red] {e}")
            return {"text": "Lo siento, tuve un pequeño problema técnico. ¿Podemos intentarlo de nuevo?", "has_changes": False}

maria = MariaMaster()