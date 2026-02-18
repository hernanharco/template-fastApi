import logging

class ResponseSanitizer:
    """
    SRP: Clase dedicada a normalizar y limpiar respuestas de IA.
    Asegura que el cliente final solo reciba texto legible. [cite: 2026-02-18]
    """

    @staticmethod
    def clean(response) -> str:
        """
        Limpia formatos de diccionario, tupla u objetos de mensaje.
        """
        # Si la respuesta es nula
        if response is None:
            return "Lo siento, no pude procesar tu solicitud. 😊"

        # Caso: Diccionario (El error que tenías: {'role':..., 'content':...})
        if isinstance(response, dict):
            print("🧹 [SANITIZER] Limpiando diccionario detectado...")
            return response.get("content", response.get("text", str(response)))

        # Caso: Tupla (A veces los orquestadores devuelven (texto, estado))
        if isinstance(response, tuple):
            print("🧹 [SANITIZER] Limpiando tupla detectada...")
            return ResponseSanitizer.clean(response[0])

        # Caso: Objeto de mensaje de LangChain (AIMessage)
        if hasattr(response, "content"):
            return str(response.content)

        # Caso: Lista (Por si acaso se devuelve un historial)
        if isinstance(response, list):
            if len(response) > 0:
                return ResponseSanitizer.clean(response[-1])
            return "Dime, ¿en qué puedo ayudarte?"

        # Caso final: Asegurar que sea string y quitar espacios extra
        return str(response).strip()