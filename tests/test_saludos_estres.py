import sys
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# 1. Configuración de rutas
ruta_proyecto = Path(__file__).parent.parent
load_dotenv(ruta_proyecto / ".env")
sys.path.insert(0, str(ruta_proyecto))

from app.db.session import SessionLocal
from app.agents.main_master import ValeriaMaster 
from app.models.clients import Client
from sqlalchemy.orm.attributes import flag_modified

class TestValeriaSaludos:
    @classmethod
    def setup_class(cls):
        """Configuración inicial: Instanciamos a la jefa."""
        cls.master = ValeriaMaster()
        cls.test_phone = "34634405549" 

    def test_saludo_con_mencion_de_servicio(self):
        """
        CASO DE FALLA 1: El usuario menciona un servicio pero solo saluda.
        """
        db = SessionLocal()
        mensaje = "Hola Valeria, que buen día para hacerse unas uñas"
        
        print(f"\n--- Probando Mensaje: '{mensaje}' ---")
        # CORRECCIÓN: Desempaquetamos la tupla (texto, estado)
        resultado, _ = self.master.process(db, self.test_phone, mensaje, [])
        
        # Ahora 'resultado' es un string y .lower() funcionará
        assert "agendada con éxito" not in resultado.lower(), "FALLA: Agendó cita ante un saludo temático"
        db.close()

    def test_saludo_con_referencia_temporal(self):
        """
        CASO DE FALLA 2: El usuario usa palabras de tiempo sin intención de reserva.
        """
        db = SessionLocal()
        mensaje = "Buenas tardes Valeria, mañana te escribo para agendar algo"
        
        print(f"\n--- Probando Mensaje: '{mensaje}' ---")
        # CORRECCIÓN: Desempaquetamos la tupla
        resultado, _ = self.master.process(db, self.test_phone, mensaje, [])
        
        assert "éxito" not in resultado.lower(), "FALLA: Capturó una cita cuando el usuario dijo que escribiría luego"
        db.close()

    def test_saludo_simple_con_memoria_sucia(self):
        """
        CASO DE FALLA 3: Usuario saluda pero tiene una cita vieja en Neon.
        """
        db = SessionLocal()
        mensaje = "Hola, ¿cómo estás?"
        
        print(f"\n--- Probando Mensaje: '{mensaje}' ---")
        client = db.query(Client).filter(Client.phone == self.test_phone).first()
        if client:
            client.metadata_json = {"appointment_date": "2026-02-25", "appointment_time": "10:00"}
            flag_modified(client, "metadata_json")
            db.commit()

        # CORRECCIÓN: Desempaquetamos la tupla
        resultado, _ = self.master.process(db, self.test_phone, mensaje, [])
        
        assert "2026-02-25" not in resultado, "FALLA: El ruteador disparó la confirmación por error de lógica"
        db.close()

# --- BLOQUE DE EJECUCIÓN ---
if __name__ == "__main__":
    tester = TestValeriaSaludos()
    tester.setup_class()
    
    print("\n" + "="*60)
    print("🚀 INICIANDO TEST DE ESTRÉS DE SALUDOS (VALERIA MASTER)")
    print("="*60)

    pruebas = [
        ("Mención de servicio", tester.test_saludo_con_mencion_de_servicio),
        ("Referencia temporal", tester.test_saludo_con_referencia_temporal),
        ("Memoria sucia (Neon)", tester.test_saludo_simple_con_memoria_sucia)
    ]

    for nombre, funcion in pruebas:
        try:
            print(f"\n🧪 {nombre}...")
            funcion()
            print(f"✅ PASÓ: {nombre}")
        except AssertionError as e:
            print(f"❌ FALLA EN {nombre}: {e}")
        except Exception as e:
            print(f"⚠️ ERROR INESPERADO EN {nombre}: {e}")

    print("\n" + "="*60)
    print("🏁 FIN DE LOS TESTS")
    print("="*60 + "\n")