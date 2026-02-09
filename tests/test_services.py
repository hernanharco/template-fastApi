"""
Tests para el dominio Services.
Cubre CRUD completo y validaciones.
"""

import pytest
from fastapi.testclient import TestClient
from app.models.services import Service


class TestServicesAPI:
    """Tests para endpoints de Services API."""
    
    def test_create_service_success(self, client: TestClient, sample_service_data):
        """Test de creación exitosa de un servicio."""
        response = client.post("/api/v1/services/", json=sample_service_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_service_data["name"]
        assert data["duration_minutes"] == sample_service_data["duration_minutes"]
        assert data["price"] == sample_service_data["price"]
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
    
    def test_create_service_invalid_name(self, client: TestClient):
        """Test de creación con nombre inválido."""
        invalid_data = {
            "name": "",  # Nombre vacío
            "duration_minutes": 30,
            "price": 150.00
        }
        
        response = client.post("/api/v1/services/", json=invalid_data)
        assert response.status_code == 422
    
    def test_create_service_invalid_duration(self, client: TestClient):
        """Test de creación con duración inválida."""
        invalid_data = {
            "name": "Manicura",
            "duration_minutes": 33,  # No es múltiplo de 5
            "price": 150.00
        }
        
        response = client.post("/api/v1/services/", json=invalid_data)
        assert response.status_code == 422
    
    def test_create_service_invalid_price(self, client: TestClient):
        """Test de creación con precio inválido."""
        invalid_data = {
            "name": "Manicura",
            "duration_minutes": 30,
            "price": 150.123  # Más de 2 decimales
        }
        
        response = client.post("/api/v1/services/", json=invalid_data)
        assert response.status_code == 422
    
    def test_get_services_empty(self, client: TestClient):
        """Test de obtener lista de servicios vacía."""
        response = client.get("/api/v1/services/")
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_services_with_data(self, client: TestClient, sample_service_data):
        """Test de obtener lista de servicios con datos."""
        # Crear un servicio primero
        client.post("/api/v1/services/", json=sample_service_data)
        
        response = client.get("/api/v1/services/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == sample_service_data["name"]
    
    def test_get_service_by_id_success(self, client: TestClient, sample_service_data):
        """Test de obtener servicio por ID exitoso."""
        # Crear servicio
        create_response = client.post("/api/v1/services/", json=sample_service_data)
        service_id = create_response.json()["id"]
        
        # Obtener por ID
        response = client.get(f"/api/v1/services/{service_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == service_id
        assert data["name"] == sample_service_data["name"]
    
    def test_get_service_by_id_not_found(self, client: TestClient):
        """Test de obtener servicio por ID inexistente."""
        response = client.get("/api/v1/services/999")
        
        assert response.status_code == 404
    
    def test_update_service_success(self, client: TestClient, sample_service_data):
        """Test de actualización exitosa de servicio."""
        # Crear servicio
        create_response = client.post("/api/v1/services/", json=sample_service_data)
        service_id = create_response.json()["id"]
        
        # Actualizar
        update_data = {
            "name": "Manicura Premium",
            "price": 200.00
        }
        response = client.put(f"/api/v1/services/{service_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["price"] == update_data["price"]
        assert data["duration_minutes"] == sample_service_data["duration_minutes"]  # No cambió
    
    def test_update_service_not_found(self, client: TestClient):
        """Test de actualizar servicio inexistente."""
        update_data = {"name": "Nuevo nombre"}
        response = client.put("/api/v1/services/999", json=update_data)
        
        assert response.status_code == 404
    
    def test_delete_service_success(self, client: TestClient, sample_service_data):
        """Test de eliminación exitosa de servicio."""
        # Crear servicio
        create_response = client.post("/api/v1/services/", json=sample_service_data)
        service_id = create_response.json()["id"]
        
        # Eliminar
        response = client.delete(f"/api/v1/services/{service_id}")
        
        assert response.status_code == 200
        assert response.json()["message"] == "Servicio eliminado exitosamente"
        
        # Verificar que el servicio sigue existiendo pero inactivo
        get_response = client.get(f"/api/v1/services/{service_id}")
        assert get_response.status_code == 200
        assert get_response.json()["is_active"] is False
    
    def test_delete_service_not_found(self, client: TestClient):
        """Test de eliminar servicio inexistente."""
        response = client.delete("/api/v1/services/999")
        
        assert response.status_code == 404
    
    def test_get_active_services_only(self, client: TestClient, sample_service_data):
        """Test de obtener solo servicios activos."""
        # Crear servicio
        create_response = client.post("/api/v1/services/", json=sample_service_data)
        service_id = create_response.json()["id"]
        
        # Obtener servicios activos (debería mostrar el servicio recién creado)
        response_active = client.get("/api/v1/services/?active_only=true")
        assert response_active.status_code == 200
        active_data = response_active.json()
        assert len(active_data) == 1  # Hay un servicio activo
        
        # Desactivar servicio
        client.put(f"/api/v1/services/{service_id}", json={"is_active": False})
        
        # Obtener servicios activos (ahora debería estar vacío)
        response = client.get("/api/v1/services/?active_only=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0  # No hay servicios activos
        
        # Obtener todos los servicios (incluyendo inactivos)
        response_all = client.get("/api/v1/services/")
        assert len(response_all.json()) == 1
        assert response_all.json()[0]["is_active"] is False


class TestServicesModel:
    """Tests para el modelo Service de SQLAlchemy."""
    
    def test_service_creation(self, db_session):
        """Test de creación de servicio en base de datos."""
        service = Service(
            name="Pedicura",
            duration_minutes=45,
            price=200.00,
            is_active=True
        )
        
        db_session.add(service)
        db_session.commit()
        db_session.refresh(service)
        
        assert service.id is not None
        assert service.name == "Pedicura"
        assert service.duration_minutes == 45
        assert service.price == 200.00
        assert service.is_active is True
        assert service.created_at is not None
        assert service.updated_at is not None
    
    def test_service_to_dict(self, db_session):
        """Test del método to_dict del modelo."""
        service = Service(
            name="Tratamiento Facial",
            duration_minutes=60,
            price=300.00
        )
        
        db_session.add(service)
        db_session.commit()
        db_session.refresh(service)
        
        service_dict = service.to_dict()
        
        assert service_dict["name"] == "Tratamiento Facial"
        assert service_dict["duration_minutes"] == 60
        assert service_dict["price"] == 300.00
        assert "created_at" in service_dict
        assert "updated_at" in service_dict
    
    def test_service_repr(self, db_session):
        """Test del método __repr__ del modelo."""
        service = Service(
            name="Masaje",
            duration_minutes=90,
            price=250.00
        )
        
        db_session.add(service)
        db_session.commit()
        db_session.refresh(service)
        
        repr_str = repr(service)
        assert "Masaje" in repr_str
        assert "90min" in repr_str
        assert "$250.0" in repr_str
