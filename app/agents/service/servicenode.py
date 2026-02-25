# app/agents/service/nodes.py
from thefuzz import process, fuzz
from langchain_core.messages import AIMessage
from datetime import datetime

from app.agents.state import AgentState  # Importación del estado centralizado
from app.db.session import SessionLocal
from app.models.services import Service

def service_expert_node(state: AgentState) -> dict:
    """
    SRP: Nodo experto en servicios.
    Responsabilidad: Validar servicios con fuzzy matching o mostrar el catálogo proactivamente.
    """
    # 1. Acceso seguro al contenido del último mensaje del usuario
    last_msg_content = ""
    if state.get("messages"):
        last_m = state["messages"][-1]
        # Soporte para objetos LangChain o diccionarios de LangGraph Studio
        last_msg_content = getattr(last_m, "content", "") or (last_m.get("content") if isinstance(last_m, dict) else "")
    
    last_msg_content = last_msg_content.lower()
    
    # 2. Conexión a Base de Datos (Neon) con Context Manager para evitar fugas de conexiones
    with SessionLocal() as db:
        services_db = db.query(Service).filter(Service.is_active == True).all()
        
        if not services_db:
            return {
                "messages": [AIMessage(content="Por ahora no tengo servicios disponibles. ¡Vuelve pronto!")],
                "current_node": "service_expert"
            }

        services_dict = {s.name.lower(): (s.name, s.id) for s in services_db}
        choices = list(services_dict.keys())

        # 3. Validación Difusa (Fuzzy Matching)
        # Solo intentamos detectar si el mensaje no es un saludo corto o genérico
        match_result = None
        if len(last_msg_content) > 3:
            match_result = process.extractOne(last_msg_content, choices, scorer=fuzz.token_set_ratio)

        # Si hay un match con alta confianza (score >= 70)
        if match_result and match_result[1] >= 70:
            name, srv_id = services_dict[match_result[0]]
            res = f"¡Excelente elección! He anotado que te interesa *{name}*. ✨\n\n¿Para qué día y hora te gustaría agendar tu cita?"
            return {
                "messages": [AIMessage(content=res)],
                "service_id": srv_id,  # <--- ¡ESTO ES VITAL! Para que el estado lo guarde
                "current_node": "service_expert",
                "last_updated": datetime.now().isoformat()
            }

        # 4. Presentación Proactiva del Catálogo
        # Se ejecuta si el usuario saludó o no especificó un servicio válido
        lines = []
        for s in services_db:
            # Iconos dinámicos según palabras clave del servicio
            icon = "💅" if any(x in s.name.lower() for x in ["uñas", "manicure", "pedicure"]) else \
                   "💇‍♀️" if any(x in s.name.lower() for x in ["corte", "cabello", "peinado"]) else "✨"
            lines.append(f"{icon} *{s.name}*")
        
        catalog = "\n".join(lines)
        
        # Recuperamos el nombre extraído por identity_node
        nombre = state.get("client_name", "cliente")
        
        # Construimos una respuesta personalizada que sirve como bienvenida y catálogo
        res = (
            f"¡Hola {nombre}! Qué gusto saludarte. ✨\n\n"
            f"Aquí tienes nuestra lista de servicios disponibles:\n\n"
            f"{catalog}\n\n"
            "¿Cuál de estos te gustaría reservar?"
        )
        
        return {
            "messages": [AIMessage(content=res)],
            "current_node": "service_expert",
            "last_updated": datetime.now().isoformat()
        }