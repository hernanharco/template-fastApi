from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

# Importamos Base desde tu configuración de base de datos
# Asegúrate de que en app/database.py tengas: Base = declarative_base()
from app.models.base import Base 

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    
    # index=True y unique=True para que las búsquedas por WhatsApp sean instantáneas 🚀
    phone = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, nullable=True)
    
    # --- MEMORIA DEL AGENTE (Lo que evita el bucle) ---
    # Guardamos el ID del servicio que el usuario eligió pero aún no agenda
    current_service_id = Column(Integer, ForeignKey("services.id"), nullable=True)
    
    # --- ANALÍTICA Y ORIGEN ---
    # Para saber si lo creó la IA o tú manualmente en el panel
    source = Column(String, default="ia", nullable=False) 
    
    # Campo flexible para verticalización (notas extras del negocio)
    metadata_json = Column(JSONB, default={})
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # --- RELACIONES --- [cite: 2026-02-13]
    # Importante: Usamos el nombre del modelo como string "Appointment" 
    # para evitar el error de importación circular que tenías.
    appointments = relationship("Appointment", back_populates="client")
    
    # Relación para acceder rápido al servicio que tiene pendiente
    current_service = relationship("Service")

    def __repr__(self):
        return f"<Client(full_name='{self.full_name}', phone='{self.phone}', source='{self.source}')>"