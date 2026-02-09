"""
Tests de integración para verificar el funcionamiento completo de la API.
Tests que involucran múltiples dominios y flujos de trabajo completos.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient


class TestIntegrationFlows:
    """Tests de integración para flujos completos de negocio."""
    
    def test_complete_booking_flow(self, client: TestClient):
        """Test del flujo completo de reserva de una cita."""
        # 1. Crear un servicio
        service_data = {
            "name": "Manicura Premium",
            "duration_minutes": 45,
            "price": 200.00
        }
        service_response = client.post("/api/v1/services/", json=service_data)
        assert service_response.status_code == 201
        service_id = service_response.json()["id"]
        
        # 2. Crear un colaborador
        collaborator_data = {
            "name": "Ana López",
            "email": "ana@example.com"
        }
        collaborator_response = client.post("/api/v1/collaborators/", json=collaborator_data)
        assert collaborator_response.status_code == 201
        collaborator_id = collaborator_response.json()["id"]
        
        # 3. Configurar horarios de negocio
        business_hours_data = {
            "day_of_week": 0,
            "day_name": "Lunes",
            "is_enabled": True,
            "is_split_shift": False,
            "time_slots": [
                {
                    "start_time": "09:00",
                    "end_time": "18:00",
                    "slot_order": 1
                }
            ]
        }
        bh_response = client.post("/api/v1/business-hours/", json=business_hours_data)
        assert bh_response.status_code == 201
        
        # 4. Crear una cita
        tomorrow = datetime.now() + timedelta(days=1)
        tomorrow = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0)
        end_time = tomorrow + timedelta(minutes=45)
        
        appointment_data = {
            "service_id": service_id,
            "collaborator_id": collaborator_id,
            "client_name": "María García",
            "client_phone": "+34 600 123 456",
            "client_email": "maria@example.com",
            "start_time": tomorrow.isoformat(),
            "end_time": end_time.isoformat(),
            "status": "scheduled"
        }
        
        appointment_response = client.post("/api/v1/appointments/", json=appointment_data)
        assert appointment_response.status_code == 201
        appointment_id = appointment_response.json()["id"]
        
        # 5. Verificar que la cita fue creada
        get_response = client.get(f"/api/v1/appointments/{appointment_id}")
        assert get_response.status_code == 200
        appointment = get_response.json()
        assert appointment["client_name"] == "María García"
        assert appointment["status"] == "scheduled"
        
        # 6. Confirmar la cita
        confirm_response = client.patch(
            f"/api/v1/appointments/{appointment_id}/status",
            json={"status": "confirmed"}
        )
        assert confirm_response.status_code == 200
        assert confirm_response.json()["status"] == "confirmed"
        
        # 7. Completar la cita
        complete_response = client.patch(
            f"/api/v1/appointments/{appointment_id}/status",
            json={"status": "completed"}
        )
        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "completed"
    
    def test_business_hours_availability_flow(self, client: TestClient):
        """Test del flujo de configuración de horarios y verificación de disponibilidad."""
        # 1. Configurar horarios para toda la semana
        days = [
            (0, "Lunes"), (1, "Martes"), (2, "Miércoles"),
            (3, "Jueves"), (4, "Viernes")
        ]
        
        for day_of_week, day_name in days:
            business_hours_data = {
                "day_of_week": day_of_week,
                "day_name": day_name,
                "is_enabled": True,
                "is_split_shift": True,
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
            response = client.post("/api/v1/business-hours/", json=business_hours_data)
            assert response.status_code == 201
        
        # 2. Verificar que los horarios se crearon correctamente
        bh_response = client.get("/api/v1/business-hours/")
        assert bh_response.status_code == 200
        business_hours = bh_response.json()
        assert len(business_hours) == 5
        
        # 3. Verificar que cada día tiene 2 time slots
        for day in business_hours:
            assert len(day["time_slots"]) == 2
            assert day["is_split_shift"] is True
    
    def test_service_management_workflow(self, client: TestClient):
        """Test del flujo completo de gestión de servicios."""
        # 1. Crear múltiples servicios
        services_data = [
            {"name": "Manicura Básica", "duration_minutes": 30, "price": 150.00},
            {"name": "Pedicura Completa", "duration_minutes": 45, "price": 200.00},
            {"name": "Tratamiento Facial", "duration_minutes": 60, "price": 300.00},
            {"name": "Masaje Relajante", "duration_minutes": 90, "price": 250.00}
        ]
        
        created_services = []
        for service_data in services_data:
            response = client.post("/api/v1/services/", json=service_data)
            assert response.status_code == 201
            created_services.append(response.json())
        
        # 2. Verificar que todos los servicios fueron creados
        all_services_response = client.get("/api/v1/services/")
        assert all_services_response.status_code == 200
        all_services = all_services_response.json()
        assert len(all_services) == 4
        
        # 3. Actualizar precios de algunos servicios
        update_data = {"price": 175.00}
        update_response = client.put(f"/api/v1/services/{created_services[0]['id']}", json=update_data)
        assert update_response.status_code == 200
        assert update_response.json()["price"] == 175.00
        
        # 4. Desactivar un servicio
        deactivate_response = client.put(
            f"/api/v1/services/{created_services[1]['id']}",
            json={"is_active": False}
        )
        assert deactivate_response.status_code == 200
        
        # 5. Verificar servicios activos
        active_services_response = client.get("/api/v1/services/?active_only=true")
        assert active_services_response.status_code == 200
        active_services = active_services_response.json()
        assert len(active_services) == 3  # Uno fue desactivado
    
    def test_collaborator_appointments_relationship(self, client: TestClient):
        """Test de la relación entre colaboradores y sus citas."""
        # 1. Crear colaboradores
        collaborators_data = [
            {"name": "Ana López", "email": "ana@example.com"},
            {"name": "María García", "email": "maria@example.com"}
        ]
        
        created_collaborators = []
        for collab_data in collaborators_data:
            response = client.post("/api/v1/collaborators/", json=collab_data)
            assert response.status_code == 201
            created_collaborators.append(response.json())
        
        # 2. Crear servicios
        service_data = {
            "name": "Manicura Express",
            "duration_minutes": 20,
            "price": 100.00
        }
        service_response = client.post("/api/v1/services/", json=service_data)
        service_id = service_response.json()["id"]
        
        # 3. Asignar múltiples citas a cada colaborador
        for i, collaborator in enumerate(created_collaborators):
            for j in range(3):  # 3 citas por colaborador
                start_time = datetime.now() + timedelta(days=i+1, hours=j+9)
                end_time = start_time + timedelta(minutes=20)
                
                appointment_data = {
                    "service_id": service_id,
                    "collaborator_id": collaborator["id"],
                    "client_name": f"Cliente {i}-{j}",
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "status": "scheduled"
                }
                
                response = client.post("/api/v1/appointments/", json=appointment_data)
                assert response.status_code == 201
        
        # 4. Verificar que cada colaborador tiene sus citas asignadas
        all_appointments_response = client.get("/api/v1/appointments/")
        assert all_appointments_response.status_code == 200
        all_appointments = all_appointments_response.json()
        assert len(all_appointments) == 6  # 2 colaboradores × 3 citas
        
        # 5. Verificar distribución de citas
        collaborator1_appointments = [
            app for app in all_appointments 
            if app["collaborator_id"] == created_collaborators[0]["id"]
        ]
        collaborator2_appointments = [
            app for app in all_appointments 
            if app["collaborator_id"] == created_collaborators[1]["id"]
        ]
        
        assert len(collaborator1_appointments) == 3
        assert len(collaborator2_appointments) == 3
    
    def test_error_handling_and_validation(self, client: TestClient):
        """Test de manejo de errores y validaciones en flujos completos."""
        # 1. Intentar crear cita con servicio inexistente
        appointment_data = {
            "service_id": 999,
            "collaborator_id": 1,
            "client_name": "Test Client",
            "start_time": "2024-12-15T10:00:00",
            "end_time": "2024-12-15T10:30:00",
            "status": "scheduled"
        }
        
        response = client.post("/api/v1/appointments/", json=appointment_data)
        assert response.status_code == 422
        
        # 2. Intentar crear servicio con datos inválidos
        invalid_service_data = {
            "name": "",  # Nombre vacío
            "duration_minutes": -10,  # Duración negativa
            "price": 0  # Precio cero
        }
        
        response = client.post("/api/v1/services/", json=invalid_service_data)
        assert response.status_code == 422
        
        # 3. Intentar crear horarios duplicados
        business_hours_data = {
            "day_of_week": 0,
            "day_name": "Lunes",
            "is_enabled": True,
            "is_split_shift": False,
            "time_slots": [{"start_time": "09:00", "end_time": "18:00", "slot_order": 1}]
        }
        
        # Primera creación debería funcionar
        response1 = client.post("/api/v1/business-hours/", json=business_hours_data)
        assert response1.status_code == 201
        
        # Segunda creación debería fallar
        response2 = client.post("/api/v1/business-hours/", json=business_hours_data)
        assert response2.status_code == 400  # O 422 dependiendo de la implementación
    
    def test_data_consistency_across_operations(self, client: TestClient):
        """Test de consistencia de datos a través de múltiples operaciones."""
        # 1. Crear servicio
        service_data = {
            "name": "Servicio Test",
            "duration_minutes": 30,
            "price": 150.00
        }
        service_response = client.post("/api/v1/services/", json=service_data)
        service_id = service_response.json()["id"]
        
        # 2. Verificar que el servicio existe
        get_service = client.get(f"/api/v1/services/{service_id}")
        assert get_service.status_code == 200
        original_service = get_service.json()
        
        # 3. Actualizar servicio
        update_data = {
            "name": "Servicio Actualizado",
            "price": 175.00
        }
        update_response = client.put(f"/api/v1/services/{service_id}", json=update_data)
        assert update_response.status_code == 200
        
        # 4. Verificar que los cambios se aplicaron
        updated_service = update_response.json()
        assert updated_service["name"] == "Servicio Actualizado"
        assert updated_service["price"] == 175.00
        assert updated_service["duration_minutes"] == original_service["duration_minutes"]  # No cambió
        
        # 5. Crear cita con el servicio actualizado
        collaborator_data = {"name": "Colaborador Test", "email": "test@example.com"}
        collaborator_response = client.post("/api/v1/collaborators/", json=collaborator_data)
        collaborator_id = collaborator_response.json()["id"]
        
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(minutes=30)
        
        appointment_data = {
            "service_id": service_id,
            "collaborator_id": collaborator_id,
            "client_name": "Cliente Test",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "status": "scheduled"
        }
        
        appointment_response = client.post("/api/v1/appointments/", json=appointment_data)
        assert appointment_response.status_code == 201
        
        # 6. Verificar que la cita está asociada al servicio correcto
        appointment = appointment_response.json()
        assert appointment["service_id"] == service_id
        
        # 7. Obtener detalles completos de la cita
        get_appointment = client.get(f"/api/v1/appointments/{appointment['id']}")
        assert get_appointment.status_code == 200
        full_appointment = get_appointment.json()
        assert full_appointment["service_id"] == service_id
        assert full_appointment["collaborator_id"] == collaborator_id
