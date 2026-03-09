from app.agents.memory.memory_service import save_message
from app.agents.memory.chat_memory import load_chat_history
from app.agents.memory.memory_detector import detect_memory
# from app.agents.memory.vector_memory import save_memory, search_memories


class MemoryOrchestrator:

    def __init__(self, db):
        self.db = db

    def store_user_message(self, phone: str, text: str):
        save_message(self.db, phone, "user", text)

        # Temporalmente desactivado mientras arreglamos pgvector
        # memory = detect_memory(text)
        # if memory:
        #     save_memory(self.db, phone, memory)

    def store_ai_message(self, phone: str, text: str):
        save_message(self.db, phone, "assistant", text)

    def build_context(self, phone: str, user_input: str):
        history = load_chat_history(self.db, phone)

        # Temporalmente desactivado mientras arreglamos pgvector
        memories = []

        memory_context = ""

        if memories:
            memory_context = "Información que recuerdas del usuario:\n"
            for m in memories:
                memory_context += f"- {m}\n"

        return history, memory_context