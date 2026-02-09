#!/usr/bin/env python3

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.models.base import Base
from app.models import services

# Base de datos en memoria para tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_simple():
    # Crear tablas
    Base.metadata.create_all(bind=engine)
    
    # Crear sesión
    db = TestingSessionLocal()
    
    # Override de la dependencia
    from app.db.session import get_db
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    try:
        with TestClient(app) as client:
            # 1. Crear servicio
            service_data = {
                "name": "Test Service",
                "duration_minutes": 30,
                "price": 150.0
            }
            create_resp = client.post("/api/v1/services/", json=service_data)
            print(f"Create: {create_resp.status_code} - {create_resp.text}")
            
            if create_resp.status_code == 201:
                service_id = create_resp.json()["id"]
                print(f"Service ID: {service_id}")
                
                # 2. Obtener todos los servicios
                all_resp = client.get("/api/v1/services/")
                print(f"All services: {all_resp.status_code} - {all_resp.text}")
                
                # 3. Desactivar servicio
                update_resp = client.put(f"/api/v1/services/{service_id}", json={"is_active": False})
                print(f"Update: {update_resp.status_code} - {update_resp.text}")
                
                # 4. Obtener todos los servicios después de desactivar
                all_resp2 = client.get("/api/v1/services/")
                print(f"All services after update: {all_resp2.status_code} - {all_resp2.text}")
                
                # 5. Obtener solo servicios activos
                active_resp = client.get("/api/v1/services/?active_only=true")
                print(f"Active services: {active_resp.status_code} - {active_resp.text}")
                
                # Verificar el test
                assert create_resp.status_code == 201
                assert len(all_resp.json()) == 1
                assert update_resp.status_code == 200
                assert len(all_resp2.json()) == 0  # El servicio desactivado no aparece
                assert len(active_resp.json()) == 0  # No hay servicios activos
                
                print("✅ Test passed!")
    finally:
        app.dependency_overrides.clear()
        db.close()
        Base.metadata.drop_all(bind=engine)

if __name__ == "__main__":
    test_simple()
