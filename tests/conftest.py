"""
Configuración de pytest con fixtures para tests.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import get_db
from app.models.base import Base
# Importar todos los modelos para que se registren
from app.models import services, business_hours, appointments, collaborators


# Base de datos en memoria para tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Fixture que proporciona una sesión de base de datos para tests.
    Crea las tablas, proporciona la sesión y las elimina al final.
    """
    # No crear tablas aquí, lo hará el fixture client
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """
    Fixture que proporciona un cliente de test para FastAPI.
    Inyecta la sesión de base de datos de测试.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Importar y crear tablas manualmente para el test
    Base.metadata.create_all(bind=engine)
    
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_service_data():
    """Fixture con datos de ejemplo para un servicio."""
    return {
        "name": "Manicura Básica",
        "duration_minutes": 30,
        "price": 150.00
    }


@pytest.fixture
def sample_business_hours_data():
    """Fixture con datos de ejemplo para horarios de negocio."""
    return {
        "day_of_week": 0,
        "day_name": "Lunes",
        "is_enabled": True,
        "is_split_shift": True,  # Cambiar a True para permitir 2 slots
        "time_slots": [
            {
                "start_time": "09:00",
                "end_time": "13:00",
                "slot_order": 1
            },
            {
                "start_time": "14:00",
                "end_time": "18:00",
                "slot_order": 2
            }
        ]
    }


@pytest.fixture
def sample_appointment_data():
    """Fixture con datos de ejemplo para una cita."""
    from datetime import datetime
    # Usar datetime con timezone awareness
    start_time = datetime(2024, 12, 15, 10, 0, 0)
    end_time = datetime(2024, 12, 15, 10, 30, 0)
    
    return {
        "service_id": 1,
        "collaborator_id": 1,
        "client_name": "María García",
        "client_phone": "+34 600 123 456",
        "client_email": "maria@example.com",
        "client_notes": "Primera vez",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "status": "scheduled"
    }
