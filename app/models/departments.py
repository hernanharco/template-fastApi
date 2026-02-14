from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base

# Tabla Intermedia: Muchos a Muchos (Colaboradores <-> Departamentos)
collaborator_departments = Table(
    "collaborator_departments",
    Base.metadata,
    Column("collaborator_id", Integer, ForeignKey("collaborators.id", ondelete="CASCADE"), primary_key=True),
    Column("department_id", Integer, ForeignKey("departments.id", ondelete="CASCADE"), primary_key=True),
)

class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # RELACIONES
    services = relationship("Service", back_populates="department")
    collaborators = relationship(
        "Collaborator", 
        secondary=collaborator_departments, 
        back_populates="departments"
    )

    def __repr__(self):
        return f"<Department(id={self.id}, name='{self.name}')>"