# app/agents/core/llm.py
# Punto central del LLM - cambiar aquí afecta a todos los nodos

from langchain_openai import ChatOpenAI

def get_llm(temperature: float = 0.0):
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=temperature,
    )