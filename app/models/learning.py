from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from app.models.base import Base  # O donde tengas tu Base de SQLAlchemy

class AiLearningLog(Base):
    __tablename__ = "ai_learning_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Datos del contexto
    phone = Column(String(20), index=True)
    module_name = Column(String(50))  # 'appointments', 'booking', etc.
    
    # Lo que pasó en la conversación
    user_message = Column(Text)
    ai_response = Column(Text)
    
    # Para control manual después
    is_resolved = Column(Boolean, default=False)  # ¿Ya corregiste este error en el código?
    notes = Column(Text, nullable=True)           # Notas sobre qué cambiaste (ej: "Añadí tardecita al config")