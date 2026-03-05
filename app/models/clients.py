# app/models/client.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base 

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, default=1) 

    full_name = Column(String, nullable=False)
    phone = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, nullable=True)
    notes = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # 🧠 ESTADO DE LA SESIÓN ACTUAL (Para la reserva que se está haciendo ahora)
    # Estos campos son volátiles: se usan mientras el cliente habla con la IA
    current_service_id = Column(Integer, nullable=True) 
    current_collaborator_id = Column(Integer, ForeignKey("collaborators.id"), nullable=True)
    
    source = Column(String, default="ia", nullable=False) 
    
    # 📂 ALMACENAMIENTO FLEXIBLE (Aquí guardamos la lista de favoritos)
    # Guardaremos: {"preferred_collaborator_ids": [1, 5, 12]}
    # Al usar JSONB en Neon, podemos hacer consultas rápidas sobre estos IDs
    metadata_json = Column(JSONB, server_default='{}', nullable=False)
        
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # --- RELACIONES ---
    # Citas históricas del cliente
    appointments = relationship("Appointment", back_populates="client")

    # Colaborador de la sesión actual (El que está "en el carrito" de la IA)
    current_collaborator = relationship("Collaborator", foreign_keys=[current_collaborator_id])

    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.full_name}', favorites={self.metadata_json.get('preferred_collaborator_ids', [])})>"