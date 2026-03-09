from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.models.base import Base


class UserMemory(Base):

    __tablename__ = "user_memories"

    id = Column(Integer, primary_key=True)

    client_phone = Column(String, index=True)

    memory = Column(String)

    embedding = Column(Vector(1536))  # embedding de OpenAI

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatMessage(Base):

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True)

    client_phone = Column(String, index=True)

    role = Column(String)  # 'user' o 'assistant'

    message = Column(String)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
