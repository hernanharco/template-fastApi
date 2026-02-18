import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Configuración de rutas
ruta_proyecto = Path(__file__).parent.parent
sys.path.insert(0, str(ruta_proyecto))

from app.db.session import SessionLocal
from app.agents.main_master import ValeriaMaster

class TestTemporalStress:
    @classmethod
    def setup_class(cls):
        cls.master = ValeriaMaster()
        cls.test_phone = "34634405549"

    def test_variaciones_temporales(self):
        db = SessionLocal()
        print("\n🚀 INICIANDO TEST DE ESTRÉS TEMPORAL (20+ ESCENARIOS)")
        
        # Simulamos que el usuario ya eligió un servicio para activar la persistencia
        # En un escenario real, esto vendría de la sesión previa en NEON
        escenarios = [
            # --- Relativos Directos ---
            "si miremos para mañana",
            "pasa para pasado mañana",
            "mejor el lunes que viene",
            "el próximo miércoles",
            "dentro de ocho días",
            "en quince días",
            
            # --- Formatos Mixtos ---
            "el 25 de este mes",
            "para el viernes a las 3 de la tarde",
            "el próximo fin de semana",
            "para el último día de febrero",
            
            # --- Expresiones Ambiguas (Peligrosas) ---
            "¿qué tienes para el martes?",
            "me sirve el jueves en la mañana",
            "¿puedo ir el lunes tipo 4pm?",
            "miremos el día después de mañana",
            "el viernes que cae 20",
            
            # --- Casos de Error/Borde ---
            "ayer me di cuenta que quiero cita para hoy", # Fecha pasada vs hoy
            "el 31 de abril", # Fecha inexistente
            "en navidad", # Festivos (si no hay lógica, debería dar error controlado)
            "para hoy mismo pero tarde",
            "en un rato si puedes",
            "el lunes sin falta",
            "para la otra semana",
            "mejora para el mes que entra",
            "el día 15",
            "mañana a primera hora"
        ]

        exitos = 0
        fallos = 0

        for frase in escenarios:
            print(f"\n📝 Probando: '{frase}'")
            
            # Estado inicial simulando que ya sabemos que quiere "Cejas"
            state_simulado = {
                "service_type": "Cejas",
                "phone": self.test_phone,
                "messages": [{"role": "user", "content": frase}]
            }
            
            # Ejecutamos el ruteo del Master
            # Queremos ver si con estas frases el Master sigue mandando a BOOKING
            ruta_final = self.master._determine_final_route(frase, "saludo", state_simulado)
            
            if ruta_final == "agendar":
                print(f"✅ Ruteo Correcto -> BOOKING")
                exitos += 1
            else:
                print(f"❌ FALLÓ -> Se fue a '{ruta_final}'")
                fallos += 1

        print("\n" + "="*40)
        print(f"📊 RESUMEN: {exitos} Pasaron | {fallos} Fallaron")
        print("="*40)
        db.close()

if __name__ == "__main__":
    tester = TestTemporalStress()
    tester.setup_class()
    tester.test_variaciones_temporales()