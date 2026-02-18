from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base
from app.models.departments import collaborator_departments

class Collaborator(Base):
    __tablename__ = "collaborators"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    email = Column(String(255), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # RELACIÓN MUCHOS A MUCHOS
    departments = relationship(
        "Department", 
        secondary=collaborator_departments, 
        back_populates="collaborators"
    )

    business_hours = relationship("BusinessHours", back_populates="collaborator", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="collaborator", cascade="all, delete-orphan")