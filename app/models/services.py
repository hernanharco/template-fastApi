from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base

class Service(Base):
    __tablename__ = "services"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # --- RELACIÓN CON DEPARTAMENTO ---
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # RELACIONES
    department = relationship("Department", back_populates="services")
    appointments = relationship("Appointment", back_populates="service", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Service(id={self.id}, name='{self.name}', dept_id={self.department_id})>"
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "duration_minutes": self.duration_minutes,
            "price": self.price,
            "is_active": self.is_active,
            "department_id": self.department_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }