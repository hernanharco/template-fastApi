import logging
from typing import Dict, Any

from app.agents.core.langgraph_client import LangGraphClient
from app.agents.core.thread_manager import ThreadManager
from app.db.session import SessionLocal
from app.agents.memory.memory_orchestrator import MemoryOrchestrator

logger = logging.getLogger(__name__)

# ── Versión del thread ────────────────────────────────────────────────────────
# Incrementa este número cuando el thread se corrompa en desarrollo
# para forzar un thread_id nuevo sin tocar la BD ni reiniciar procesos.
# En producción siempre debe ser "" (string vacío).
_THREAD_VERSION = "v3"
# ─────────────────────────────────────────────────────────────────────────────


class MariaMaster:

    def __init__(self):
        self.client = LangGraphClient("http://localhost:2024")
        self.assistant_id = "mariamaster"

    async def process_message(self, phone: str, user_input: str) -> Dict[str, Any]:
        thread_id = ThreadManager.build_thread_id(phone + _THREAD_VERSION)

        db = SessionLocal()
        memory = MemoryOrchestrator(db)

        try:
            memory.store_user_message(phone, user_input)

            _, memory_context = memory.build_context(phone, user_input)

            payload = {
                "messages": [
                    {"role": "user", "content": user_input}
                ],
                "client_phone": phone,
                "memories": memory_context,
            }

            await self.client.ensure_thread(thread_id)

            state = await self.client.run_agent(
                thread_id=thread_id,
                assistant_id=self.assistant_id,
                payload=payload,
            )

            ai_text = self._extract_response_text(state)

            memory.store_ai_message(phone, ai_text)

            return {"text": ai_text}

        except Exception:
            logger.exception("LangGraph communication error")
            return {"text": "Ups, hubo un problema procesando tu mensaje."}

        finally:
            db.close()

    def _extract_response_text(self, state: dict) -> str:
        if not state:
            return "No pude generar respuesta."

        values = state.get("values", state)

        response_text = values.get("response_text")
        if response_text:
            return response_text

        messages = values.get("messages", [])

        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "assistant":
                return msg.get("content", "")

            if hasattr(msg, "type") and msg.type == "ai":
                return msg.content

        return "No pude generar respuesta."


maria_master = MariaMaster()