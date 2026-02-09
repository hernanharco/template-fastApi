#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app

def test_debug():
    client = TestClient(app)
    
    # Datos de prueba
    business_hours_data = {
        "day_of_week": 0,
        "day_name": "Lunes",
        "is_enabled": True,
        "is_split_shift": False,
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
    
    print("Enviando datos:", business_hours_data)
    
    # 1. Crear business hours
    create_resp = client.post("/api/v1/business-hours/", json=business_hours_data)
    print(f"Create: {create_resp.status_code}")
    print(f"Response: {create_resp.text}")
    
    if create_resp.status_code != 201:
        print("Error details:")
        try:
            error_data = create_resp.json()
            print(f"  Detail: {error_data.get('detail')}")
        except:
            print("  No se pudo parsear el error")

if __name__ == "__main__":
    test_debug()
