from sqlalchemy.orm import Session
from sqlalchemy import text
from openai import OpenAI

from app.agents.memory.memory_models import UserMemory
from app.core.config import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY)


# crear embedding
def create_embedding(text: str):

    response = client.embeddings.create(model="text-embedding-3-small", input=text)

    return response.data[0].embedding


# guardar recuerdo
def save_memory(db: Session, phone: str, text: str):

    embedding = create_embedding(text)

    memory = UserMemory(client_phone=phone, memory=text, embedding=embedding)

    db.add(memory)
    db.commit()


# buscar recuerdos similares
def search_memories(db: Session, phone: str, query: str, limit: int = 3):

    embedding = create_embedding(query)

    sql = text(
        """
    SELECT memory
    FROM user_memories
    WHERE client_phone = :phone
    ORDER BY embedding <-> :embedding
    LIMIT :limit
    """
    )

    result = db.execute(sql, {"phone": phone, "embedding": embedding, "limit": limit})

    return [row[0] for row in result]
