from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from app.models.base import Base
from datetime import datetime

class AIAuditLog(Base):
    """
    SRP: Representar la persistencia física de una interacción de IA para auditoría.
    """
    __tablename__ = "ai_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(20), index=True)
    user_message = Column(Text)
    detected_intent = Column(String(50))
    detected_service = Column(String(50))
    final_response = Column(Text)
    
    # JSONB en Postgres (NEON) es perfecto para guardar el estado completo
    state_before = Column(JSON) 
    state_after = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)