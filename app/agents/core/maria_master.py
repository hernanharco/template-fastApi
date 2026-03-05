import traceback
import logging
from typing import Dict, Any
import uuid
from rich.console import Console
from rich.panel import Panel
from langgraph_sdk import get_client

console = Console()
logger = logging.getLogger(__name__)


class MariaMaster:
    """
    🎯 Orquestador Master de María:
    Conecta el Webhook de FastAPI con el servidor de LangGraph (Desarrollo Local).
    Usa el thread_id para mantener la persistencia de IDs de servicios y horarios.
    """

    def __init__(self, url: str = "http://localhost:2024"):
        # La URL debe coincidir con el puerto donde corre 'langgraph dev'
        self.url = url
        # El assistant_id debe ser el nombre definido en tu archivo langgraph.json
        self.assistant_id = "mariamaster"

    async def process_message(self, phone: str, user_input: str) -> Dict[str, Any]:
        """
        Procesa el mensaje del usuario manteniendo la persistencia por hilo (Thread).
        """
        # Generamos un ID de hilo único por teléfono para mantener la memoria
        thread_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"whatsapp_{phone}")
        thread_id = str(thread_uuid)

        console.print(
            f"\n[bold cyan]🤖 María Master:[/bold cyan] Enviando a servidor LangGraph (Thread: [yellow]{thread_id}[/yellow])"
        )

        try:
            client = get_client(url=self.url)

            # --- 🛡️ ASEGURAR QUE EL HILO EXISTA ---
            try:
                await client.threads.get(thread_id)
            except Exception:
                # Si no existe (404), lo creamos primero
                await client.threads.create(thread_id=thread_id)
                console.print(f"[yellow]🧵 Hilo nuevo creado en servidor:[/yellow] {thread_id}")

            # 2. Ejecución
            await client.runs.wait(
                thread_id=thread_id,
                assistant_id=self.assistant_id,
                input={
                    "messages": [{"role": "user", "content": user_input}],
                    "client_phone": phone,
                },
            )

            # 3. Recuperamos el estado final del hilo para obtener la respuesta de la IA
            state = await client.threads.get_state(thread_id)

            # 4. Extracción segura del último mensaje generado por la IA
            values = state.get("values", {})
            messages = values.get("messages", [])

            ai_response = "Lo siento, tuve un problema al procesar tu mensaje."

            if messages:
                # El servidor devuelve diccionarios, buscamos el último con rol 'assistant' o 'ai'
                for msg in reversed(messages):
                    # Manejo flexible si el mensaje es un dict o un objeto
                    content = (
                        msg.get("content")
                        if isinstance(msg, dict)
                        else getattr(msg, "content", None)
                    )
                    role = (
                        msg.get("role")
                        if isinstance(msg, dict)
                        else getattr(msg, "role", None)
                    )
                    msg_type = (
                        msg.get("type")
                        if isinstance(msg, dict)
                        else getattr(msg, "type", None)
                    )

                    if (role in ["assistant", "ai"] or msg_type == "ai") and content:
                        ai_response = content
                        break

            # 5. Telemetría de Rich para depuración visual
            self._print_debug_panel(state)

            return {"text": ai_response, "has_changes": False}

        except Exception as e:
            console.print(
                f"[bold red]❌ Error en comunicación con LangGraph:[/bold red] {str(e)}"
            )
            # Imprimimos el error completo en consola para diagnóstico
            traceback.print_exc()
            return {
                "text": "Ups, mi conexión se interrumpió un momento. ¿Podrías decirme eso de nuevo?",
                "has_changes": False,
            }

    def _print_debug_panel(self, state: dict):
        """
        Muestra en la terminal los datos que el servidor está recordando.
        """
        values = state.get("values", {})
        ids = values.get("shown_service_ids", [])
        slots = values.get("active_slots", [])
        name = values.get("client_name", "Desconocido")

        console.print(
            Panel(
                f"👤 [bold white]Cliente:[/bold white] {name}\n"
                f"📦 [bold green]IDs en Memoria:[/bold green] {ids}\n"
                f"🕒 [bold blue]Horarios en Memoria:[/bold blue] {len(slots)} slots",
                title="[bold magenta]DEBUG: Estado del Hilo[/bold magenta]",
                expand=False,
            )
        )


# Instancia lista para usar en tus endpoints
maria_master = MariaMaster()
