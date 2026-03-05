# tests/test_booking_scheduler.py
import unittest
from datetime import datetime, date
from unittest.mock import Mock, patch
import sys
import os

# Agregar el path del proyecto para poder importar
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.booking_scheduler import (
    get_booking_options_with_favorites,
    get_next_available_dates,
    confirm_booking_option,
)


class TestBookingScheduler(unittest.TestCase):

    def test_get_booking_options_with_favorites_success(self):
        """Test que verifica la obtención de opciones con favoritos"""

        # Mock de la base de datos y modelos
        mock_db = Mock()

        # Mock cliente con favoritos
        mock_client = Mock()
        mock_client.full_name = "Juan Pérez"
        mock_client.metadata_json = {"preferred_collaborator_ids": [1, 3]}

        # Mock servicio
        mock_service = Mock()
        mock_service.name = "Corte de Cabello"
        mock_service.duration_minutes = 30

        # Mock slots disponibles
        mock_slots = [
            {
                "start_time": datetime(2026, 3, 4, 10, 0),
                "collaborator_id": 1,
                "collaborator_name": "María García",
            },
            {
                "start_time": datetime(2026, 3, 4, 11, 0),
                "collaborator_id": 3,
                "collaborator_name": "Ana López",
            },
        ]

        # Configurar mocks
        mock_db.query.return_value.filter.return_value.first.return_value = mock_client
        with patch(
            "app.services.booking_scheduler.get_available_slots",
            return_value=mock_slots,
        ):
            mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = (
                mock_service
            )

            # Ejecutar la función
            result = get_booking_options_with_favorites(
                db=mock_db,
                client_phone="34634405549",
                service_id=1,
                target_date=date(2026, 3, 4),
            )

            # Verificaciones
            self.assertTrue(result["success"])
            self.assertEqual(result["service"], "Corte de Cabello")
            self.assertEqual(result["date"], "04/03/2026")
            self.assertEqual(result["client"], "Juan Pérez")
            self.assertTrue(result["has_favorites"])
            self.assertEqual(len(result["options"]), 2)

            # Verificar formato de opciones
            option1 = result["options"][0]
            self.assertEqual(option1["option_number"], 1)
            self.assertEqual(option1["time"], "10:00")
            self.assertEqual(option1["collaborator"], "María García")
            self.assertTrue(option1["is_favorite"])

    def test_get_booking_options_no_favorites(self):
        """Test que verifica la obtención de opciones sin favoritos"""

        mock_db = Mock()

        # Mock cliente sin favoritos
        mock_client = Mock()
        mock_client.full_name = "Carlos Ruiz"
        mock_client.metadata_json = {"preferred_collaborator_ids": []}

        # Mock servicio
        mock_service = Mock()
        mock_service.name = "Pedicure"
        mock_service.duration_minutes = 45

        # Mock slots (sin favoritos)
        mock_slots = [
            {
                "start_time": datetime(2026, 3, 4, 14, 0),
                "collaborator_id": 2,
                "collaborator_name": "Laura Martínez",
            },
            {
                "start_time": datetime(2026, 3, 4, 15, 0),
                "collaborator_id": 4,
                "collaborator_name": "Sofía Castro",
            },
        ]

        mock_db.query.return_value.filter.return_value.first.return_value = mock_client
        with patch(
            "app.services.booking_scheduler.get_available_slots",
            return_value=mock_slots,
        ):
            mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = (
                mock_service
            )

            result = get_booking_options_with_favorites(
                db=mock_db,
                client_phone="34634405550",
                service_id=2,
                target_date=date(2026, 3, 4),
            )

            self.assertTrue(result["success"])
            self.assertFalse(result["has_favorites"])
            self.assertEqual(len(result["options"]), 2)

            # Verificar que no son favoritos
            for option in result["options"]:
                self.assertFalse(option["is_favorite"])

    def test_confirm_booking_option_success(self):
        """Test que verifica la confirmación exitosa de una cita"""

        mock_db = Mock()

        # Mock servicio
        mock_service = Mock()
        mock_service.name = "Corte de Cabello"
        mock_service.duration_minutes = 30

        mock_db.query.return_value.filter.return_value.first.return_value = mock_service

        result = confirm_booking_option(
            db=mock_db,
            client_phone="34634405549",
            service_id=1,
            collaborator_id=1,
            selected_datetime="2026-03-04 10:00",
        )

        self.assertTrue(result["success"])
        self.assertIn("Cita confirmada", result["message"])
        self.assertEqual(result["appointment"]["service"], "Corte de Cabello")
        self.assertEqual(result["appointment"]["datetime"], "04/03/2026 a las 10:00")
        self.assertEqual(result["appointment"]["duration"], 30)


if __name__ == "__main__":
    print("🧪 Ejecutando tests de Booking Scheduler...")
    unittest.main(verbosity=2)
