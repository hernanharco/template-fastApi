import sys
import os
from pathlib import Path

# 1. Configuración de rutas para encontrar 'app'
ruta_proyecto = Path(__file__).parent.parent
sys.path.insert(0, str(ruta_proyecto))

class TestMasterLogic:
    """
    Test de Integración para la lógica de ruteo del Master.
    Verifica que las decisiones de negocio sobrepasen los errores de la IA.
    """

    def setup_method(self):
        """
        Reemplaza al __init__. Se ejecuta antes de cada test. [cite: 2026-02-18]
        """
        from app.agents.main_master import ValeriaMaster
        self.master = ValeriaMaster()

    def test_continuacion_cita_evita_bucle(self):
        """
        ESCENARIO 1: El usuario ya eligió cejas y dice 'mañana'.
        No debe volver al saludo aunque la intención parezca saludo.
        """
        print("\n🚩 Probando: Continuación de cita (Evitar bucle)")
        state = {
            "client_name": "Hernan",
            "service_type": "Cejas",
            "messages": [{"role": "user", "content": "si miremos mañana"}]
        }
        intent_ia = "saludo" # Simulación de error de la IA
        
        # Probamos la lógica de decisión
        final_route = self.master._determine_final_route("si miremos mañana", intent_ia, state)
        
        assert final_route == "agendar", f"❌ FALLÓ: Mandó a '{final_route}' en lugar de seguir agendando."
        print("✅ PASÓ: El sistema priorizó la reserva sobre el saludo.")

    def test_agendar_sin_servicio_redirige_a_catalogo(self):
        """
        ESCENARIO 2: El usuario quiere cita pero no sabemos de qué.
        Debe ir a SERVICE para mostrar el catálogo. [cite: 2026-02-13]
        """
        print("\n🚩 Probando: Agendar sin servicio previo")
        state = {
            "client_name": "Hernan",
            "service_type": None,
            "messages": [{"role": "user", "content": "quiero una cita"}]
        }
        intent_ia = "agendar"
        
        final_route = self.master._determine_final_route("quiero una cita", intent_ia, state)
        
        assert final_route == "ver_catalogo", f"❌ FALLÓ: Mandó a '{final_route}' sin tener servicio definido."
        print("✅ PASÓ: El sistema redirigió correctamente al catálogo.")

    def test_saludo_puro_va_a_identity(self):
        """
        ESCENARIO 3: Un 'Hola' seco sin contexto previo.
        Debe ir a IDENTITY para el saludo oficial.
        """
        print("\n🚩 Probando: Saludo inicial puro")
        state = {"service_type": None, "messages": []}
        intent_ia = "saludo"
        
        final_route = self.master._determine_final_route("Hola", intent_ia, state)
        
        assert final_route == "saludo", f"❌ FALLÓ: No reconoció un saludo inicial estándar."
        print("✅ PASÓ: Ruteo a Identity correcto.")

# --- Bloque para ejecución manual si no usas pytest ---
if __name__ == "__main__":
    tester = TestMasterLogic()
    tester.setup_method()
    tester.test_continuacion_cita_evita_bucle()
    tester.test_agendar_sin_servicio_redirige_a_catalogo()
    tester.test_saludo_puro_va_a_identity()