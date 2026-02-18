import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Configuración de rutas
ruta_proyecto = Path(__file__).parent.parent
sys.path.insert(0, str(ruta_proyecto))

from app.db.session import SessionLocal
from app.agents.booking.orchestrator import BookingOrchestrator

class TestBookingFlow:
    """
    Test de flujo: Verifica la transición de fechas cuando no hay cupo.
    [cite: 2026-02-13]
    """

    def setup_method(self):
        self.orchestrator = BookingOrchestrator()
        self.db = SessionLocal()
        self.test_phone = "34634405549"

    def teardown_method(self):
        self.db.close()

    def test_transicion_a_manana_cuando_hoy_esta_lleno(self):
        print("\n🚀 Probando flujo: 'Hoy lleno -> Sugerir mañana'")
        
        # 1. Simulamos que el usuario pide Cejas para HOY
        hoy_str = datetime.now().strftime("%Y-%m-%d")
        state = {
            "phone": self.test_phone,
            "service_type": "Cejas",
            "appointment_date": hoy_str,
            "messages": []
        }

        # Ejecutamos el orquestador
        # Nota: Asumimos que hoy no hay cupo en tu DB de pruebas o simulamos la respuesta
        res, messages = self.orchestrator.process_booking(self.db, state, "")

        print(f"🔹 Respuesta recibida: {res}")

        # VALIDACIÓN 1: ¿Sugirió mañana?
        manana_obj = datetime.now() + timedelta(days=1)
        fecha_esperada = manana_obj.strftime("%d/%m")
        
        assert fecha_esperada in res, f"❌ ERROR: No sugirió la fecha de mañana ({fecha_esperada})"
        
        # VALIDACIÓN 2: ¿Reseteó la fecha en el estado? 
        # (Esto es lo que arreglamos para que el extractor actúe en el siguiente turno)
        assert state["appointment_date"] is None, "❌ ERROR: El estado no limpió la fecha para permitir la nueva extracción"
        
        print("✅ PASÓ: El orquestador sugirió mañana y limpió el estado correctamente.")

    def test_formato_fecha_amigable(self):
        print("\n🚀 Probando: Formato de fecha amigable (DD/MM/YYYY)")
        
        fecha_iso = "2026-02-20"
        res_fmt = self.orchestrator._fmt_date(fecha_iso)
        
        assert res_fmt == "20/02/2026", f"❌ ERROR: Formato incorrecto. Recibido: {res_fmt}"
        print(f"✅ PASÓ: Fecha convertida correctamente: {res_fmt}")

if __name__ == "__main__":
    # Ejecución manual rápida
    tester = TestBookingFlow()
    tester.setup_method()
    tester.test_transicion_a_manana_cuando_hoy_esta_lleno()
    tester.test_formato_fecha_amigable()
    tester.teardown_method()