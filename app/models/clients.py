from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from .base import Base  # Importamos la Base que me mostraste
from sqlalchemy.orm import relationship

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    # index=True y unique=True son vitales para que el buscador por móvil vuele 🚀
    phone = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, nullable=True)
    
    # Campo flexible para verticalización (notas, etiquetas, etc.)
    metadata_json = Column(JSONB, default={})
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relación inversa: Un cliente tiene muchas citas
    appointments = relationship("Appointment", back_populates="client")