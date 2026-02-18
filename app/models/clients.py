from sqlalchemy import Column, Integer, String, DateTime, Boolean
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
    
    # 🧠 CAMPOS VITALES PARA LA IA (ValeriaMaster)
    # Al ponerlos como Columnas normales, la IA puede leerlos/escribirlos sin error
    current_service_id = Column(Integer, nullable=True) 
    source = Column(String, default="ia", nullable=False) 
    
    # Aquí es donde la IA suele guardar contexto adicional
    metadata_json = Column(JSONB, server_default='{}', nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relación con citas para que Valeria pueda agendar
    appointments = relationship("Appointment", back_populates="client")

    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.full_name}')>"