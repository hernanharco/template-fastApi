# app/agents/identity/identitynode.py
from datetime import datetime
from langchain_core.messages import AIMessage
from openai import OpenAI
from rich import print as rprint  # Usamos rich para que los debugs resalten

from app.core.settings import settings
from app.db.session import SessionLocal
from app.models.clients import Client
from app.agents.identity.client_service import get_or_create_client_by_phone
from app.agents.state import AgentState

def identity_node(state: AgentState) -> dict:
    """
    SRP: Nodo de Identidad.
    Responsabilidad: Identificar al cliente o extraer su nombre.
    """
    rprint("[bold yellow]🔍 DEBUG: Entrando en identity_node...[/bold yellow]")
    
    biz_name = getattr(settings, "BUSINESS_NAME", "nuestra estética")
    phone = state.get("client_phone")
    
    # 1. Extraer el contenido del último mensaje del usuario
    last_msg_content = ""
    if state.get("messages"):
        last_m = state["messages"][-1]
        # Manejo de compatibilidad si el mensaje viene como objeto o dict
        last_msg_content = getattr(last_m, "content", "") or (last_m.get("content") if isinstance(last_m, dict) else "")

    # 2. Conexión a Base de Datos (Neon)
    with SessionLocal() as db:
        rprint(f"[bold yellow]🔍 DEBUG: Consultando DB para el teléfono: {phone}[/bold yellow]")
        client_db = db.query(Client).filter(Client.phone == phone).first()

        # CASO A: El cliente YA existe con nombre real
        if client_db and client_db.full_name and client_db.full_name != "Nuevo Cliente":
            rprint(f"[bold green]✅ DEBUG: Cliente reconocido: {client_db.full_name}[/bold green]")
            return {
                "client_name": client_db.full_name,
                "current_node": "identity",
                "last_updated": datetime.now().isoformat()
            }

        # CASO B: Intentar extraer nombre si el usuario respondió a la pregunta
        rprint("[bold yellow]🔍 DEBUG: No hay nombre real. Intentando extraer con OpenAI...[/bold yellow]")
        
        # PROMPT DE EXTRACCIÓN
        extraction_prompt = (
            f"El usuario dice: '{last_msg_content}'. "
            "Si el usuario se está presentando o dando su nombre, responde SOLO el nombre propio. "
            "Si no hay un nombre claro (ej: dice 'hola', 'buenas', 'que tal'), responde 'NONE'."
        )

        try:
            # IMPORTANTE: Asegúrate de que settings.OPENAI_API_KEY esté configurada
            client_ai = OpenAI(api_key=settings.OPENAI_API_KEY) 
            
            res = client_ai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": extraction_prompt}],
                temperature=0,
                timeout=10 # Evitamos que se quede colgado eternamente
            )
            detected_name = res.choices[0].message.content.strip()
            rprint(f"[bold yellow]🔍 DEBUG: OpenAI devolvió: {detected_name}[/bold yellow]")

            # Si detectamos un nombre real, lo guardamos
            if "NONE" not in detected_name.upper() and len(detected_name) > 1:
                rprint(f"[bold green]✨ DEBUG: ¡Nombre detectado!: {detected_name}[/bold green]")
                # Actualizamos en DB
                if client_db:
                    client_db.full_name = detected_name
                    db.commit()
                
                return {
                    "messages": [AIMessage(content=f"¡Mucho gusto, {detected_name}! Ya te registré. Dime, ¿en qué puedo ayudarte hoy? 💇‍♀️")],
                    "client_name": detected_name,
                    "current_node": "identity",
                    "last_updated": datetime.now().isoformat()
                }
        
        except Exception as e:
            rprint(f"[bold red]❌ ERROR EN OPENAI (identity_node): {str(e)}[/bold red]")
            # Si falla la IA, no bloqueamos el flujo, seguimos al Caso C

    # CASO C: No se pudo detectar nombre o es el primer mensaje
    rprint("[bold blue]👋 DEBUG: Emitiendo pregunta de presentación inicial.[/bold blue]")
    return {
        "messages": [AIMessage(content=f"¡Hola! Bienvenido a {biz_name}. Soy Maria, ¿me podrías decir tu nombre para atenderte mejor? 😊")],
        "client_name": "Nuevo Cliente", # Mantenemos el placeholder
        "current_node": "identity",
        "last_updated": datetime.now().isoformat()
    }