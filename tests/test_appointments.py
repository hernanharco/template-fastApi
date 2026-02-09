"""
Tests para el dominio Appointments.
Cubre CRUD completo y validaciones de citas.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.models.appointments import Appointment, AppointmentStatus
from app.models.services import Service
from app.models.collaborators import Collaborator


class TestAppointmentsAPI:
    """Tests para endpoints de Appointments API."""
    
    def setup_test_data(self, client: TestClient):
        """Configura datos de prueba para los tests."""
        # Crear servicio
        service_data = {
            "name": "Manicura Básica",
            "duration_minutes": 30,
            "price": 150.00
        }
        service_response = client.post("/api/v1/services/", json=service_data)
        service_id = service_response.json()["id"]
        
        # Crear colaborador
        collaborator_data = {
            "name": "Ana López",
            "email": "ana@example.com"
        }
        collaborator_response = client.post("/api/v1/collaborators/", json=collaborator_data)
        collaborator_id = collaborator_response.json()["id"]
        
        return service_id, collaborator_id
    
    def test_create_appointment_success(self, client: TestClient, sample_appointment_data):
        """Test de creación exitosa de una cita."""
        service_id, collaborator_id = self.setup_test_data(client)
        
        appointment_data = sample_appointment_data.copy()
        appointment_data["service_id"] = service_id
        appointment_data["collaborator_id"] = collaborator_id
        
        response = client.post("/api/v1/appointments/", json=appointment_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["service_id"] == service_id
        assert data["collaborator_id"] == collaborator_id
        assert data["client_name"] == appointment_data["client_name"]
        assert data["status"] == "scheduled"
        assert "id" in data
    
    def test_create_appointment_invalid_service(self, client: TestClient, sample_appointment_data):
        """Test de creación con servicio inexistente."""
        appointment_data = sample_appointment_data.copy()
        appointment_data["service_id"] = 999
        appointment_data["collaborator_id"] = 1
        
        response = client.post("/api/v1/appointments/", json=appointment_data)
        
        assert response.status_code == 400  # Validación de foreign key
    
    def test_create_appointment_invalid_collaborator(self, client: TestClient, sample_appointment_data):
        """Test de creación con colaborador inexistente."""
        service_id, _ = self.setup_test_data(client)
        
        appointment_data = sample_appointment_data.copy()
        appointment_data["service_id"] = service_id
        appointment_data["collaborator_id"] = 999
        
        response = client.post("/api/v1/appointments/", json=appointment_data)
        
        assert response.status_code == 400  # Validación de foreign key
    
    def test_create_appointment_invalid_datetime(self, client: TestClient, sample_appointment_data):
        """Test de creación con datetime inválido."""
        service_id, collaborator_id = self.setup_test_data(client)
        
        appointment_data = sample_appointment_data.copy()
        appointment_data["service_id"] = service_id
        appointment_data["collaborator_id"] = collaborator_id
        appointment_data["start_time"] = "2024-12-15T18:00:00"
        appointment_data["end_time"] = "2024-12-15T10:00:00"  # Fin antes que inicio
        
        response = client.post("/api/v1/appointments/", json=appointment_data)
        
        assert response.status_code == 422
    
    def test_get_appointments_empty(self, client: TestClient):
        """Test de obtener lista de citas vacía."""
        response = client.get("/api/v1/appointments/")
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_get_appointments_with_data(self, client: TestClient, sample_appointment_data):
        """Test de obtener lista de citas con datos."""
        service_id, collaborator_id = self.setup_test_data(client)
        
        appointment_data = sample_appointment_data.copy()
        appointment_data["service_id"] = service_id
        appointment_data["collaborator_id"] = collaborator_id
        
        # Crear cita
        client.post("/api/v1/appointments/", json=appointment_data)
        
        # Obtener lista
        response = client.get("/api/v1/appointments/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["client_name"] == appointment_data["client_name"]
    
    def test_get_appointment_by_id_success(self, client: TestClient, sample_appointment_data):
        """Test de obtener cita por ID exitoso."""
        service_id, collaborator_id = self.setup_test_data(client)
        
        appointment_data = sample_appointment_data.copy()
        appointment_data["service_id"] = service_id
        appointment_data["collaborator_id"] = collaborator_id
        
        # Crear cita
        create_response = client.post("/api/v1/appointments/", json=appointment_data)
        appointment_id = create_response.json()["id"]
        
        # Obtener por ID
        response = client.get(f"/api/v1/appointments/{appointment_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == appointment_id
        assert data["client_name"] == appointment_data["client_name"]
    
    def test_get_appointment_by_id_not_found(self, client: TestClient):
        """Test de obtener cita por ID inexistente."""
        response = client.get("/api/v1/appointments/999")
        
        assert response.status_code == 404
    
    def test_update_appointment_success(self, client: TestClient, sample_appointment_data):
        """Test de actualización exitosa de cita."""
        service_id, collaborator_id = self.setup_test_data(client)
        
        appointment_data = sample_appointment_data.copy()
        appointment_data["service_id"] = service_id
        appointment_data["collaborator_id"] = collaborator_id
        
        # Crear cita
        create_response = client.post("/api/v1/appointments/", json=appointment_data)
        appointment_id = create_response.json()["id"]
        
        # Actualizar
        update_data = {
            "client_name": "María Rodríguez",
            "status": "confirmed"
        }
        response = client.put(f"/api/v1/appointments/{appointment_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["client_name"] == update_data["client_name"]
        assert data["status"] == update_data["status"]
    
    def test_update_appointment_status(self, client: TestClient, sample_appointment_data):
        """Test de actualización de estado de cita."""
        service_id, collaborator_id = self.setup_test_data(client)
        
        appointment_data = sample_appointment_data.copy()
        appointment_data["service_id"] = service_id
        appointment_data["collaborator_id"] = collaborator_id
        
        # Crear cita
        create_response = client.post("/api/v1/appointments/", json=appointment_data)
        appointment_id = create_response.json()["id"]
        
        # Actualizar estado
        status_data = {"status": "completed"}
        response = client.patch(f"/api/v1/appointments/{appointment_id}/status", json=status_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
    
    def test_delete_appointment_success(self, client: TestClient, sample_appointment_data):
        """Test de eliminación exitosa de cita."""
        service_id, collaborator_id = self.setup_test_data(client)
        
        appointment_data = sample_appointment_data.copy()
        appointment_data["service_id"] = service_id
        appointment_data["collaborator_id"] = collaborator_id
        
        # Crear cita
        create_response = client.post("/api/v1/appointments/", json=appointment_data)
        appointment_id = create_response.json()["id"]
        
        # Eliminar
        response = client.delete(f"/api/v1/appointments/{appointment_id}")
        
        assert response.status_code == 200
        
        # Verificar que no existe
        get_response = client.get(f"/api/v1/appointments/{appointment_id}")
        assert get_response.status_code == 404
    
    def test_get_appointments_by_date_range(self, client: TestClient, sample_appointment_data):
        """Test de obtener citas por rango de fechas."""
        service_id, collaborator_id = self.setup_test_data(client)
        
        # Crear cita para hoy
        today = datetime.now()
        appointment_data = sample_appointment_data.copy()
        appointment_data["service_id"] = service_id
        appointment_data["collaborator_id"] = collaborator_id
        appointment_data["start_time"] = today.isoformat()
        appointment_data["end_time"] = (today + timedelta(minutes=30)).isoformat()
        
        client.post("/api/v1/appointments/", json=appointment_data)
        
        # Crear cita para mañana
        tomorrow = today + timedelta(days=1)
        appointment_data["start_time"] = tomorrow.isoformat()
        appointment_data["end_time"] = (tomorrow + timedelta(minutes=30)).isoformat()
        
        client.post("/api/v1/appointments/", json=appointment_data)
        
        # Obtener citas de hoy
        start_date = today.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        end_date = today.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
        
        response = client.get(f"/api/v1/appointments/?start_date={start_date}&end_date={end_date}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1  # Solo la cita de hoy


class TestAppointmentsModel:
    """Tests para el modelo Appointment de SQLAlchemy."""
    
    def test_appointment_creation(self, db_session):
        """Test de creación de cita en base de datos."""
        # Crear servicio
        service = Service(
            name="Manicura",
            duration_minutes=30,
            price=150.00
        )
        db_session.add(service)
        db_session.commit()
        db_session.refresh(service)
        
        # Crear colaborador
        collaborator = Collaborator(
            name="Ana López",
            email="ana@example.com"
        )
        db_session.add(collaborator)
        db_session.commit()
        db_session.refresh(collaborator)
        
        # Crear cita
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(minutes=30)
        
        appointment = Appointment(
            service_id=service.id,
            collaborator_id=collaborator.id,
            client_name="María García",
            client_phone="+34 600 123 456",
            start_time=start_time,
            end_time=end_time,
            status=AppointmentStatus.SCHEDULED
        )
        
        db_session.add(appointment)
        db_session.commit()
        db_session.refresh(appointment)
        
        assert appointment.id is not None
        assert appointment.service_id == service.id
        assert appointment.collaborator_id == collaborator.id
        assert appointment.client_name == "María García"
        assert appointment.status == AppointmentStatus.SCHEDULED
        assert appointment.created_at is not None
    
    def test_appointment_duration_minutes(self, db_session):
        """Test de la propiedad duration_minutes."""
        service = Service(name="Pedicura", duration_minutes=45, price=200.00)
        db_session.add(service)
        db_session.commit()
        db_session.refresh(service)
        
        collaborator = Collaborator(name="Juan Pérez", email="juan@example.com")
        db_session.add(collaborator)
        db_session.commit()
        db_session.refresh(collaborator)
        
        start_time = datetime.now() + timedelta(hours=2)
        end_time = start_time + timedelta(minutes=45)
        
        appointment = Appointment(
            service_id=service.id,
            collaborator_id=collaborator.id,
            client_name="Laura Sánchez",
            start_time=start_time,
            end_time=end_time
        )
        
        db_session.add(appointment)
        db_session.commit()
        db_session.refresh(appointment)
        
        assert appointment.duration_minutes == 45
    
    def test_appointment_is_active(self, db_session):
        """Test de la propiedad is_active."""
        service = Service(name="Tratamiento", duration_minutes=60, price=300.00)
        db_session.add(service)
        db_session.commit()
        db_session.refresh(service)
        
        collaborator = Collaborator(name="Carlos Ruiz", email="carlos@example.com")
        db_session.add(collaborator)
        db_session.commit()
        db_session.refresh(collaborator)
        
        start_time = datetime.now() + timedelta(hours=3)
        end_time = start_time + timedelta(minutes=60)
        
        appointment = Appointment(
            service_id=service.id,
            collaborator_id=collaborator.id,
            client_name="Sofía Martín",
            start_time=start_time,
            end_time=end_time,
            status=AppointmentStatus.SCHEDULED
        )
        
        db_session.add(appointment)
        db_session.commit()
        db_session.refresh(appointment)
        
        assert appointment.is_active is True
        
        # Cambiar a estado completado
        appointment.status = AppointmentStatus.COMPLETED
        db_session.commit()
        
        assert appointment.is_active is False
    
    def test_appointment_to_dict(self, db_session):
        """Test del método to_dict del modelo."""
        service = Service(name="Masaje", duration_minutes=90, price=250.00)
        db_session.add(service)
        db_session.commit()
        db_session.refresh(service)
        
        collaborator = Collaborator(name="Elena Gómez", email="elena@example.com")
        db_session.add(collaborator)
        db_session.commit()
        db_session.refresh(collaborator)
        
        start_time = datetime.now() + timedelta(hours=4)
        end_time = start_time + timedelta(minutes=90)
        
        appointment = Appointment(
            service_id=service.id,
            collaborator_id=collaborator.id,
            client_name="Patricia Díaz",
            client_phone="+34 600 987 654",
            start_time=start_time,
            end_time=end_time,
            status=AppointmentStatus.CONFIRMED
        )
        
        db_session.add(appointment)
        db_session.commit()
        db_session.refresh(appointment)
        
        appointment_dict = appointment.to_dict()
        
        assert appointment_dict["client_name"] == "Patricia Díaz"
        assert appointment_dict["client_phone"] == "+34 600 987 654"
        assert appointment_dict["status"] == "confirmed"
        assert "created_at" in appointment_dict
        assert "updated_at" in appointment_dict
    
    def test_appointment_repr(self, db_session):
        """Test del método __repr__ del modelo."""
        service = Service(name="Depilación", duration_minutes=20, price=100.00)
        db_session.add(service)
        db_session.commit()
        db_session.refresh(service)
        
        collaborator = Collaborator(name="Lucía Hernández", email="lucia@example.com")
        db_session.add(collaborator)
        db_session.commit()
        db_session.refresh(collaborator)
        
        start_time = datetime.now() + timedelta(hours=5)
        end_time = start_time + timedelta(minutes=20)
        
        appointment = Appointment(
            service_id=service.id,
            collaborator_id=collaborator.id,
            client_name="Carmen Ortiz",
            start_time=start_time,
            end_time=end_time
        )
        
        db_session.add(appointment)
        db_session.commit()
        db_session.refresh(appointment)
        
        repr_str = repr(appointment)
        assert "Carmen Ortiz" in repr_str
        assert "scheduled" in repr_str
