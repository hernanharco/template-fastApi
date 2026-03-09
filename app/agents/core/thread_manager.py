import uuid

# Responsable de la memoria por usuario.

class ThreadManager:

    @staticmethod
    def build_thread_id(phone: str) -> str:

        thread_uuid = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"whatsapp_{phone}",
        )

        return str(thread_uuid)


# import uuid


# class ThreadManager:

#     @staticmethod
#     def build_thread_id(phone: str) -> str:
#         """
#         Temporalmente usamos UUID aleatorio para evitar que LangGraph
#         reutilice estado viejo del hilo mientras depuramos.
#         """
#         return str(uuid.uuid4())