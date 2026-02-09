#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app

def test_debug():
    client = TestClient(app)
    
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

if __name__ == "__main__":
    test_debug()
