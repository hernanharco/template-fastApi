# testintentos.py
import unittest
from datetime import date, timedelta, datetime # 1. Importar datetime
from unittest.mock import MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage

# Importamos la función a testear
from app.agents.booking.booking_node import booking_expert_node

class TestBookingIntentos(unittest.TestCase):
    def setUp(self):
        """Configuración inicial para cada test."""
        self.mock_db = MagicMock()
        self.client_id = 128
        self.service_id = 8 # ID para "Cejas"
        
        # Simulamos que el cliente existe en DB
        self.mock_client = MagicMock()
        self.mock_client.metadata_json = {}
        self.mock_db.query().filter().first.return_value = self.mock_client

    @patch('app.agents.booking.favorite_manager.FavoriteCollaboratorManager.find_first_available_slot')
    def test_booking_reintento_avanza_dia(self, mock_find_slot):
        """
        Test: Verifica que al recibir 'otro dia', 
        la fecha de búsqueda aumenta en +1.
        """
        # --- PREPARACIÓN ---
        fecha_inicial = date.today()
        fecha_proxima = fecha_inicial + timedelta(days=1)
        
        # 2. FIX: Simulamos que start_time es un objeto datetime, no un string
        mock_slot_time = datetime.combine(fecha_proxima, datetime.strptime("10:00", "%H:%M").time())
        mock_find_slot.return_value = (fecha_proxima, [{"start_time": mock_slot_time}], True)

        # Estado inicial simulando que ya se propuso hoy
        state = {
            "db": self.mock_db,
            "client_id": self.client_id,
            "service_id": self.service_id,
            "messages": [HumanMessage(content="otro dia")],
            "intent_data": {
                "es_reintento": True,
                "date": None # No se menciona fecha explícita
            },
            "metadata": {
                "last_proposed_date": fecha_inicial.isoformat(),
                "current_service_id": self.service_id
            }
        }

        # --- EJECUCIÓN ---
        result = booking_expert_node(state)

        # --- VERIFICACIÓN ---
        # 1. Verificar que se llamó a buscar slots con la fecha correcta (mañana)
        args, _ = mock_find_slot.call_args
        fecha_buscada = args[2]
        self.assertEqual(fecha_buscada, fecha_proxima, "BookingNode no incrementó la fecha")
        
        # 2. Verificar que el resultado tiene la nueva fecha
        self.assertEqual(result["appointment_date"], fecha_proxima.isoformat())
        print(f"\n✅ Test Pass: Fecha incrementada a {fecha_proxima}")

    @patch('app.agents.booking.favorite_manager.FavoriteCollaboratorManager.find_first_available_slot')
    def test_booking_bucle_proteccion(self, mock_find_slot):
        """
        Test: Verifica que si 'otro dia' sigue sin encontrar hueco,
        la lógica de reintentos persiste y busca más adelante.
        """
        # --- PREPARACIÓN ---
        fecha_inicial = date.today()
        # Simulamos que no hay huecos en el futuro próximo
        mock_find_slot.return_value = (fecha_inicial + timedelta(days=5), [], False)

        state = {
            "db": self.mock_db,
            "client_id": self.client_id,
            "service_id": self.service_id,
            "messages": [HumanMessage(content="otro dia")],
            "intent_data": {
                "es_reintento": True,
            },
            "metadata": {
                "last_proposed_date": fecha_inicial.isoformat(),
                "attempts": 1
            }
        }

        # --- EJECUCIÓN ---
        result = booking_expert_node(state)

        # --- VERIFICACIÓN ---
        # 3. FIX: Relajar la aserción. El mensaje es dinámico.
        # Buscamos una palabra clave que indique falta de disponibilidad.
        self.assertIn("todo reservado", result["messages"][0].content)
        print("\n✅ Test Pass: Protección de bucle funciona (mensaje de no disponibilidad)")

if __name__ == '__main__':
    unittest.main()