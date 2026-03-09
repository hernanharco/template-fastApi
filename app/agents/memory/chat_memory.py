from app.agents.memory.memory_service import get_recent_messages


def load_chat_history(db, phone: str) -> list[dict]:
    messages = get_recent_messages(db, phone)

    history = []

    for m in messages:
        history.append({
            "role": m.role,
            "content": m.message
        })

    return history