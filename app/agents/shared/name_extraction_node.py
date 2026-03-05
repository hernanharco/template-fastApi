# app/agents/core/name_extraction_node.py
"""
SRP: Nodo de Extracción de Nombres
Responsabilidad única: Decidir si se necesita extraer nombre y forzar la llamada a la herramienta
"""
from langchain_core.messages import AIMessage, SystemMessage
from app.agents.shared.state import AgentState
from app.agents.shared.name_extractor import name_extractor, NameExtractionResult
from rich.console import Console

console = Console()

# System message específico para extracción de nombres
NAME_EXTRACTION_SYSTEM_PROMPT = """Eres un experto en identificar nombres propios de clientes.

REGLAS CRÍTICAS:
1. Si el usuario fue preguntado por su nombre en el mensaje anterior, CUALQUIER respuesta que dé es probablemente su nombre.
2. Si el usuario dice "me llamo X", "soy X", "mi nombre es X", extrae X.
3. Si el usuario responde con una sola palabra después de preguntarle su nombre, esa palabra es su nombre.
4. Si el nombre tiene 2+ caracteres y parece razonable, extráelo.
5. NO extraigas palabras comunes como "hola", "gracias", "bien", etc.

EJEMPLOS:
- Pregunta: "¿Cuál es tu nombre?" → Respuesta: "Hernan" → Extraer: "Hernan"
- Pregunta: "¿Cómo te llamas?" → Respuesta: "María García" → Extraer: "María García"
- Usuario: "me llamo Carlos" → Extraer: "Carlos"
- Usuario: "soy Ana" → Extraer: "Ana"

Sé preciso pero flexible. Es mejor extraer un nombre dudoso que omitir uno real."""

async def name_extraction_node(state: AgentState):
    """
    Nodo especializado en extracción de nombres con SRP
    """
    console.print("[bold magenta]🎭 Entrando a node: name_extraction_node[/bold magenta]")
    
    messages = state.get("messages", [])
    client_name = state.get("client_name")
    client_phone = state.get("client_phone")
    
    if not messages:
        return {"messages": messages, "client_name": client_name}
    
    last_message = messages[-1]
    user_text = last_message.content.strip() if hasattr(last_message, 'content') else ""
    
    # Solo procesar si no hay nombre o es un nombre genérico
    if not client_name or client_name in ["DESCONOCIDO", "Cliente", "Nuevo Cliente"]:
        console.print(f"[dim]🔍 Analizando para extracción: '{user_text}'[/dim]")
        
        # Usar el extractor especializado
        extraction_result = name_extractor.extract_name(user_text, messages)
        
        if extraction_result.name and extraction_result.confidence >= 0.7:
            console.print(f"[bold green]✅ Nombre extraído con alta confianza: '{extraction_result.name}'[/bold green]")
            console.print(f"[dim]📊 Método: {extraction_result.method} (confianza: {extraction_result.confidence})[/dim]")
            
            # Forzar llamada a herramienta con el nombre extraído
            tool_call = {
                "name": "identify_or_create_client",
                "args": {
                    "phone": client_phone,
                    "full_name": extraction_result.name,  # 🚀 NOMBRE EXTRAÍDO REAL
                },
                "id": f"name_extraction_{len(messages)}",
            }
            
            # Crear AIMessage con tool_call
            ai_message = AIMessage(
                content=f"He identificado que tu nombre es {extraction_result.name}.",
                tool_calls=[tool_call]
            )
            
            return {
                "messages": messages + [ai_message],
                "client_name": extraction_result.name,  # Actualizar estado inmediatamente
            }
        else:
            console.print(f"[dim]⚠️ No se pudo extraer nombre con confianza suficiente[/dim]")
            console.print(f"[dim]📊 Mejor resultado: '{extraction_result.name}' (confianza: {extraction_result.confidence})[/dim]")
            
            # No forzar llamada, dejar que el flujo continúe normalmente
            return {
                "messages": messages,
                "client_name": client_name,
            }
    else:
        console.print(f"[dim]✅ Cliente ya tiene nombre: '{client_name}'[/dim]")
        return {
            "messages": messages,
            "client_name": client_name,
        }

# System message para el LLM (opcional, para respuestas naturales)
def get_name_extraction_system_message() -> SystemMessage:
    """Retorna el system message para extracción de nombres"""
    return SystemMessage(content=NAME_EXTRACTION_SYSTEM_PROMPT)
