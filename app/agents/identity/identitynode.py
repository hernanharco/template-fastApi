# app/agents/identity/identitynode.py
from datetime import datetime
from langchain_core.messages import AIMessage
from rich import print as rprint

from app.core.settings import settings
from app.db.session import SessionLocal
from app.models.clients import Client
from app.models.services import Service
from app.agents.state import AgentState
# 🚀 Importamos tu nuevo extractor
from app.agents.identity.extractor_identity import extract_name_from_text

def identity_node(state: AgentState) -> dict:
    """
    SRP: Director de Identidad.
    Usa 'extract_name_from_text' para la lógica de IA y gestiona la DB.
    """
    rprint("[bold yellow]🔍 DEBUG: Entrando en identity_node (Arquitectura Modular)...[/bold yellow]")
    
    biz_name = getattr(settings, "BUSINESS_NAME", "nuestra estética")
    phone = state.get("client_phone")
    
    # 1. Obtener el mensaje del usuario de forma segura
    messages = state.get("messages", [])
    last_msg_content = ""
    if messages:
        last_m = messages[-1]
        last_msg_content = getattr(last_m, "content", "") or (last_m.get("content") if isinstance(last_m, dict) else "")

    with SessionLocal() as db:
        rprint(f"[bold yellow]🔍 DEBUG: Consultando DB para el teléfono: {phone}[/bold yellow]")
        client_db = db.query(Client).filter(Client.phone == phone).first()

        # CASO A: Cliente ya conocido (Flujo rápido)
        if client_db and client_db.full_name and client_db.full_name != "Nuevo Cliente":
            rprint(f"[bold green]✅ DEBUG: Cliente reconocido: {client_db.full_name}[/bold green]")
            return {
                "client_name": client_db.full_name,
                "current_node": "identity"
            }

        # CASO B: Cliente nuevo o sin nombre -> Usamos el Extractor
        rprint("[bold yellow]🧠 DEBUG: Llamando al Extractor de Identidad...[/bold yellow]")
        detected_name = extract_name_from_text(last_msg_content)

        if detected_name and "NONE" not in detected_name.upper():
            rprint(f"[bold green]✨ DEBUG: ¡Nombre extraído!: {detected_name}[/bold green]")
            
            # Guardamos en Neon
            if client_db:
                client_db.full_name = detected_name
                db.commit()
            
            # 🎁 PARCHE DE VALOR: Obtenemos servicios activos
            services_db = db.query(Service).filter(Service.is_active == True).all()
            
            lista_txt = ""
            for s in services_db:
                emoji = "💅" if "Manicure" in s.name else "💇‍♀️" if "Corte" in s.name else "✨"
                lista_txt += f"{emoji} {s.name}\n"

            res_content = (
                f"¡Mucho gusto, {detected_name}! ✨ Ya te registré.\n\n"
                f"Aquí tienes nuestros servicios disponibles:\n\n"
                f"{lista_txt}\n"
                "¿Cuál de estos te gustaría reservar?"
            )

            return {
                "messages": [AIMessage(content=res_content)],
                "client_name": detected_name,
                "current_node": "service_expert" # 🚀 Movimiento estratégico al siguiente nodo
            }

    # CASO C: Saludo inicial si no hay nombre ni historial
    rprint("[bold blue]👋 DEBUG: Pidiendo nombre al cliente.[/bold blue]")
    return {
        "messages": [AIMessage(content=f"¡Hola! Bienvenido a {biz_name}. Soy Maria, ¿me podrías decir tu nombre para atenderte mejor? 😊")],
        "client_name": "Nuevo Cliente",
        "current_node": "identity"
    }