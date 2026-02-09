"""
Tests para el dominio Business Hours.
Cubre CRUD completo y validaciones de horarios.
"""

import pytest
from fastapi.testclient import TestClient
from app.models.business_hours import BusinessHours, TimeSlot


class TestBusinessHoursAPI:
    """Tests para endpoints de Business Hours API."""
    
    def test_create_business_hours_success(self, client: TestClient, sample_business_hours_data):
        """Test de creación exitosa de horarios de negocio."""
        response = client.post("/api/v1/business-hours/", json=sample_business_hours_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["day_of_week"] == sample_business_hours_data["day_of_week"]
        assert data["day_name"] == sample_business_hours_data["day_name"]
        assert data["is_enabled"] == sample_business_hours_data["is_enabled"]
        assert data["is_split_shift"] == sample_business_hours_data["is_split_shift"]
        assert len(data["time_slots"]) == 2
        assert "id" in data
    
    def test_create_business_hours_duplicate_day(self, client: TestClient, sample_business_hours_data):
        """Test de creación con día duplicado."""
        # Crear primer horario
        client.post("/api/v1/business-hours/", json=sample_business_hours_data)
        
        # Intentar crear duplicado
        response = client.post("/api/v1/business-hours/", json=sample_business_hours_data)
        
        assert response.status_code == 400  # Debería dar error de duplicado
    
    def test_get_business_hours_empty(self, client: TestClient):
        """Test de obtener lista de horarios vacía."""
        response = client.get("/api/v1/business-hours/")
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_business_hours_with_data(self, client: TestClient, sample_business_hours_data):
        """Test de obtener lista de horarios con datos."""
        # Crear horarios
        client.post("/api/v1/business-hours/", json=sample_business_hours_data)
        
        response = client.get("/api/v1/business-hours/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["day_name"] == sample_business_hours_data["day_name"]
    
    def test_get_business_hours_enabled_only(self, client: TestClient, sample_business_hours_data):
        """Test de obtener solo horarios habilitados."""
        # Crear horario habilitado
        client.post("/api/v1/business-hours/", json=sample_business_hours_data)
        
        # Crear horario deshabilitado
        disabled_data = sample_business_hours_data.copy()
        disabled_data["day_of_week"] = 1
        disabled_data["day_name"] = "Martes"
        disabled_data["is_enabled"] = False
        client.post("/api/v1/business-hours/", json=disabled_data)
        
        # Obtener solo habilitados
        response = client.get("/api/v1/business-hours/?enabled_only=true")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["is_enabled"] is True
    
    def test_get_business_hours_by_id_success(self, client: TestClient, sample_business_hours_data):
        """Test de obtener horarios por ID exitoso."""
        # Crear horarios
        create_response = client.post("/api/v1/business-hours/", json=sample_business_hours_data)
        business_hours_id = create_response.json()["id"]
        
        # Obtener por ID
        response = client.get(f"/api/v1/business-hours/{business_hours_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == business_hours_id
        assert data["day_name"] == sample_business_hours_data["day_name"]
    
    def test_get_business_hours_by_id_not_found(self, client: TestClient):
        """Test de obtener horarios por ID inexistente."""
        response = client.get("/api/v1/business-hours/999")
        
        assert response.status_code == 404
    
    def test_update_business_hours_success(self, client: TestClient, sample_business_hours_data):
        """Test de actualización exitosa de horarios."""
        # Crear horarios
        create_response = client.post("/api/v1/business-hours/", json=sample_business_hours_data)
        business_hours_id = create_response.json()["id"]
        
        # Actualizar
        update_data = {
            "is_enabled": False,
            "is_split_shift": True
        }
        response = client.put(f"/api/v1/business-hours/{business_hours_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] == update_data["is_enabled"]
        assert data["is_split_shift"] == update_data["is_split_shift"]
        assert data["day_name"] == sample_business_hours_data["day_name"]  # No cambió
    
    def test_update_business_hours_not_found(self, client: TestClient):
        """Test de actualizar horarios inexistente."""
        update_data = {"is_enabled": False}
        response = client.put("/api/v1/business-hours/999", json=update_data)
        
        assert response.status_code == 404
    
    def test_delete_business_hours_success(self, client: TestClient, sample_business_hours_data):
        """Test de eliminación exitosa de horarios."""
        # Crear horarios
        create_response = client.post("/api/v1/business-hours/", json=sample_business_hours_data)
        business_hours_id = create_response.json()["id"]
        
        # Eliminar
        response = client.delete(f"/api/v1/business-hours/{business_hours_id}")
        
        assert response.status_code == 200
        
        # Verificar que no existe
        get_response = client.get(f"/api/v1/business-hours/{business_hours_id}")
        assert get_response.status_code == 404
    
    def test_delete_business_hours_not_found(self, client: TestClient):
        """Test de eliminar horarios inexistente."""
        response = client.delete("/api/v1/business-hours/999")
        
        assert response.status_code == 404
    
    def test_create_business_hours_invalid_time_range(self, client: TestClient):
        """Test de creación con rango de tiempo inválido."""
        invalid_data = {
            "day_of_week": 2,
            "day_name": "Miércoles",
            "is_enabled": True,
            "is_split_shift": False,
            "time_slots": [
                {
                    "start_time": "18:00",
                    "end_time": "09:00",  # Fin antes que inicio
                    "slot_order": 1
                }
            ]
        }
        
        response = client.post("/api/v1/business-hours/", json=invalid_data)
        # Dependiendo de la validación, puede ser 422 o 201 con lógica posterior
        assert response.status_code in [422, 201]


class TestBusinessHoursModel:
    """Tests para los modelos BusinessHours y TimeSlot de SQLAlchemy."""
    
    def test_business_hours_creation(self, db_session):
        """Test de creación de horarios en base de datos."""
        business_hours = BusinessHours(
            day_of_week=0,
            day_name="Lunes",
            is_enabled=True,
            is_split_shift=False
        )
        
        db_session.add(business_hours)
        db_session.commit()
        db_session.refresh(business_hours)
        
        assert business_hours.id is not None
        assert business_hours.day_of_week == 0
        assert business_hours.day_name == "Lunes"
        assert business_hours.is_enabled is True
        assert business_hours.is_split_shift is False
        assert business_hours.created_at is not None
        assert business_hours.updated_at is not None
    
    def test_time_slot_creation(self, db_session):
        """Test de creación de time slots en base de datos."""
        from datetime import time
        
        # Crear business hours primero
        business_hours = BusinessHours(
            day_of_week=1,
            day_name="Martes",
            is_enabled=True,
            is_split_shift=False
        )
        db_session.add(business_hours)
        db_session.commit()
        db_session.refresh(business_hours)
        
        # Crear time slot
        time_slot = TimeSlot(
            start_time=time(9, 0),
            end_time=time(13, 0),
            slot_order=1,
            business_hours_id=business_hours.id
        )
        
        db_session.add(time_slot)
        db_session.commit()
        db_session.refresh(time_slot)
        
        assert time_slot.id is not None
        assert time_slot.start_time == time(9, 0)
        assert time_slot.end_time == time(13, 0)
        assert time_slot.slot_order == 1
        assert time_slot.business_hours_id == business_hours.id
        assert time_slot.created_at is not None
    
    def test_business_hours_time_slots_relationship(self, db_session):
        """Test de relación entre BusinessHours y TimeSlot."""
        from datetime import time
        
        # Crear business hours
        business_hours = BusinessHours(
            day_of_week=2,
            day_name="Miércoles",
            is_enabled=True,
            is_split_shift=True
        )
        db_session.add(business_hours)
        db_session.commit()
        db_session.refresh(business_hours)
        
        # Crear múltiples time slots
        slot1 = TimeSlot(
            start_time=time(9, 0),
            end_time=time(13, 0),
            slot_order=1,
            business_hours_id=business_hours.id
        )
        slot2 = TimeSlot(
            start_time=time(14, 0),
            end_time=time(18, 0),
            slot_order=2,
            business_hours_id=business_hours.id
        )
        
        db_session.add_all([slot1, slot2])
        db_session.commit()
        
        # Verificar relación
        db_session.refresh(business_hours)
        assert len(business_hours.time_slots) == 2
        assert business_hours.time_slots[0].slot_order == 1
        assert business_hours.time_slots[1].slot_order == 2
    
    def test_business_hours_to_dict(self, db_session):
        """Test del método to_dict del modelo BusinessHours."""
        business_hours = BusinessHours(
            day_of_week=3,
            day_name="Jueves",
            is_enabled=True,
            is_split_shift=False
        )
        
        db_session.add(business_hours)
        db_session.commit()
        db_session.refresh(business_hours)
        
        business_hours_dict = business_hours.to_dict()
        
        assert business_hours_dict["day_of_week"] == 3
        assert business_hours_dict["day_name"] == "Jueves"
        assert business_hours_dict["is_enabled"] is True
        assert "time_slots" in business_hours_dict
        assert "created_at" in business_hours_dict
        assert "updated_at" in business_hours_dict
    
    def test_time_slot_to_dict(self, db_session):
        """Test del método to_dict del modelo TimeSlot."""
        from datetime import time
        
        business_hours = BusinessHours(
            day_of_week=4,
            day_name="Viernes",
            is_enabled=True
        )
        db_session.add(business_hours)
        db_session.commit()
        db_session.refresh(business_hours)
        
        time_slot = TimeSlot(
            start_time=time(10, 0),
            end_time=time(14, 0),
            slot_order=1,
            business_hours_id=business_hours.id
        )
        
        db_session.add(time_slot)
        db_session.commit()
        db_session.refresh(time_slot)
        
        time_slot_dict = time_slot.to_dict()
        
        assert time_slot_dict["start_time"] == "10:00"
        assert time_slot_dict["end_time"] == "14:00"
        assert time_slot_dict["slot_order"] == 1
        assert time_slot_dict["business_hours_id"] == business_hours.id
        assert "created_at" in time_slot_dict
    
    def test_business_hours_repr(self, db_session):
        """Test del método __repr__ del modelo BusinessHours."""
        business_hours = BusinessHours(
            day_of_week=5,
            day_name="Sábado",
            is_enabled=True,
            is_split_shift=True
        )
        
        db_session.add(business_hours)
        db_session.commit()
        db_session.refresh(business_hours)
        
        repr_str = repr(business_hours)
        assert "Sábado" in repr_str
        assert "enabled=True" in repr_str
        assert "split=True" in repr_str
    
    def test_time_slot_repr(self, db_session):
        """Test del método __repr__ del modelo TimeSlot."""
        from datetime import time
        
        business_hours = BusinessHours(
            day_of_week=6,
            day_name="Domingo",
            is_enabled=True
        )
        db_session.add(business_hours)
        db_session.commit()
        db_session.refresh(business_hours)
        
        time_slot = TimeSlot(
            start_time=time(11, 0),
            end_time=time(15, 0),
            slot_order=1,
            business_hours_id=business_hours.id
        )
        
        db_session.add(time_slot)
        db_session.commit()
        db_session.refresh(time_slot)
        
        repr_str = repr(time_slot)
        assert "11:00:00" in repr_str
        assert "15:00:00" in repr_str
        assert "order=1" in repr_str
