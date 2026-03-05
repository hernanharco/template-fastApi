# app/agents/core/llm.py
from langchain_openai import ChatOpenAI
# 🟢 Importamos nuestra configuración centralizada
from app.core.config import settings 

def get_llm():
    """
    Configura e instancia el modelo de lenguaje (LLM) utilizando 
    la API Key centralizada en la configuración.
    """
    
    # Validamos que la API KEY exista
    if not settings.OPENAI_API_KEY:
        raise ValueError("La variable OPENAI_API_KEY no está configurada en el archivo .env")

    return ChatOpenAI(
        model="gpt-4o", 
        temperature=0,
        # 🟢 Usamos la configuración de Pydantic
        openai_api_key=settings.OPENAI_API_KEY 
    )