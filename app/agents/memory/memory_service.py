from sqlalchemy.orm import Session
from typing import List

from app.agents.memory.memory_models import ChatMessage


def save_message(db: Session, phone: str, role: str, message: str):
    msg = ChatMessage(
        client_phone=phone,
        role=role,
        message=message,
    )

    db.add(msg)
    db.commit()


def get_recent_messages(db: Session, phone: str, limit: int = 10):

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.client_phone == phone)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )

    return list(reversed(messages))