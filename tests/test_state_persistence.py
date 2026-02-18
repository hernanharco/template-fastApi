import sys
from pathlib import Path

# 1. Configuración de Rutas para que reconozca la carpeta 'app'
ruta_proyecto = Path(__file__).parent.parent
sys.path.insert(0, str(ruta_proyecto))

from app.db.session import SessionLocal
from app.agents.main_master import ValeriaMaster
from app.models.clients import Client

class TestStatePersistence:
    """
    SRP: Validar que Valeria mantenga el hilo de la conversación (Memoria de Hierro)
    incluso cuando el usuario no repite el servicio en cada mensaje. [cite: 2026-02-13]
    """

    def setup_method(self):
        """Prepara el entorno antes de cada test."""
        self.master = ValeriaMaster()
        self.db = SessionLocal()
        self.phone = "34634405549"
        
        # Limpiamos o preparamos el cliente de prueba en NEON
        client = self.db.query(Client).filter(Client.phone == self.phone).first()
        if not client:
            client = Client(
                full_name="Hernan Test",
                phone=self.phone,
                metadata_json={}
            )
            self.db.add(client)
            self.db.commit()
        self.client = client

    def teardown_method(self):
        """Cierra la conexión al terminar."""
        self.db.close()

    def test_flujo_confirmacion_mañana(self):
        """
        CASO: El usuario aceptó 'Cejas' antes, y ahora solo dice 'si miremos para mañana'.
        El sistema DEBE recordar que son 'Cejas' y mandarlo a BOOKING.
        """
        print("\n🧪 Iniciando test: Persistencia de 'Cejas' + Confirmación Temporal")

        # 1. PRE-CONDICIÓN: Simulamos que ya eligió 'Cejas' guardándolo en NEON
        self.client.full_name = "Hernan Arango"
        self.client.metadata_json = {"service_type": "Cejas"}
        self.db.add(self.client)
        self.db.commit()
        self.db.refresh(self.client)
        
        print(f"✅ Pre-condición: NEON actualizado para {self.client.full_name}")

        # 2. ACCIÓN: El mensaje "trampa" que no menciona el servicio
        mensaje_usuario = "si miremos para mañana"
        print(f"📥 Usuario envía: '{mensaje_usuario}'")
        
        # Ejecutamos el proceso completo del Master
        respuesta, estado = self.master.process(self.db, self.phone, mensaje_usuario, [])

        # 3. VERIFICACIONES (ASSERTIONS)
        
        # A. ¿El estado que devuelve el Master sigue teniendo el servicio?
        assert estado.get("service_type") == "Cejas", \
            f"❌ FALLO: La memoria se borró. Se obtuvo: {estado.get('service_type')}"
        
        # B. ¿El texto de respuesta es de agenda (Booking) y no de saludo/catálogo?
        # Buscamos palabras que el BookingOrchestrator suele usar
        res_lower = respuesta.lower()
        palabras_booking = ["tengo", "disponible", "hueco", "horario", "mañana", "agendar"]
        hubo_ruteo_correcto = any(word in res_lower for word in palabras_booking)
        
        assert hubo_ruteo_correcto, \
            f"❌ FALLO: El ruteo fue incorrecto. Valeria respondió algo que no es de agenda: '{respuesta[:100]}...'"

        print(f"📤 Respuesta final de Valeria: {respuesta[:70]}...")
        print("✅ ÉXITO: El test pasó. Valeria tiene memoria de elefante.")

if __name__ == "__main__":
    # Para ejecutar manualmente: pytest tests/test_state_persistence.py
    pass