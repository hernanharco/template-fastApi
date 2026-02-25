from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from app.models.base import Base

class ApiRouteMetric(Base):
    __tablename__ = "api_route_metrics"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String(255), nullable=False)        # Ejemplo: /api/v1/appointments/
    method = Column(String(10), nullable=False)       # GET, POST, etc.
    status_code = Column(Integer)                     # 200, 404, 500
    process_time = Column(Float)                      # Cuánto tardó en segundos
    created_at = Column(DateTime(timezone=True), server_default=func.now())