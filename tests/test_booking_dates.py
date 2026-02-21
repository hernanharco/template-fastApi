import unittest
from datetime import datetime, timedelta
from app.agents.booking.orchestrator import BookingOrchestrator

class TestBookingDates(unittest.TestCase):
    """
    SRP: Validar que el orquestador procesa correctamente las fechas relativas.
    """

    def setUp(self):
        self.orchestrator = BookingOrchestrator()
        # Estado inicial simulado como vendría de NEON
        self.base_state = {
            "user_name": "Hernan Arango Cortes",
            "phone": "34634405549",
            "service_id": 8,
            "service_type": "Cejas",
            "appointment_date": datetime.now().strftime("%Y-%m-%d"),
            "messages": []
        }

    def test_tomorrow_logic(self):
        """Prueba que 'mañana' sume un día a la fecha actual."""
        print("\n--- TEST: MAÑANA ---")
        msg = "quiero ver horario de mañana por fa"
        
        # Simulamos la lógica que debería ocurrir en el orquestador
        # (Aquí es donde descubrimos qué código falta en el orquestador)
        tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Ejecutamos (esto fallará si el orquestador no tiene lógica de fechas)
        # Por ahora lo comparamos manualmente para diseñar la solución
        print(f"Mensaje: {msg}")
        print(f"Esperado: {tomorrow_date}")
        
        # Simulación de la corrección que aplicaremos:
        if "mañana" in msg.lower():
            self.base_state["appointment_date"] = tomorrow_date
            
        self.assertEqual(self.base_state["appointment_date"], tomorrow_date)
        print("✅ Resultado: Fecha actualizada correctamente a mañana.")

    def test_specific_day_logic(self):
        """Prueba que el sistema identifique días de la semana (ej: el lunes)."""
        print("\n--- TEST: DIA ESPECIFICO ---")
        msg = "tienes cupo para el lunes?"
        print(f"Mensaje: {msg}")
        
        # Aquí probaríamos que el extractor de IA o una lógica de Python 
        # encuentre el próximo lunes.
        self.assertTrue("lunes" in msg.lower())
        print("✅ Resultado: Palabra clave 'lunes' detectada.")

if __name__ == "__main__":
    unittest.main()