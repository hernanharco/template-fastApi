import requests
from langchain_core.tools import tool

class InventoryService:
    """
    Servicio encargado de la lógica de negocio externa (APIs y cálculos).
    Responsabilidad Única: Proveer datos y operaciones al agente.
    """
    
    @staticmethod
    @tool
    def get_categories() -> str:
        """
        Consulta las categorías reales desde la API de Platzi Fake Store.
        Útil para evitar alucinaciones del modelo.
        """
        url = "https://api.escuelajs.co/api/v1/categories"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            # Extraemos solo el nombre para simplificar el contexto del LLM
            categories = [cat["name"] for cat in response.json()]
            return ", ".join(categories)
        except Exception as e:
            return f"Error al recuperar categorías: {str(e)}"

    @staticmethod
    @tool
    def multiply(a: int, b: int) -> int:
        """Multiplica dos números enteros de forma precisa."""
        return a * b