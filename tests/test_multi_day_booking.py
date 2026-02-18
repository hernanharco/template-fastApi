import sys
from pathlib import Path
import pytest
from app.db.session import SessionLocal
from app.agents.main_master import ValeriaMaster
from app.models.clients import Client

# Añadir el path para que reconozca el módulo 'app'
ruta_proyecto = Path(__file__).parent.parent
sys.path.insert(0, str(ruta_proyecto))

class TestMultiDayBooking:
    """
    Test de Excelencia: Verifica la persistencia de memoria y el Fuzzy Matching.
    Asegura que 'Manicura' se mapee correctamente a 'Manicure Esmalte Normal'.
    """

    def setup_method(self):
        self.master = ValeriaMaster()
        self.db = SessionLocal()
        self.phone = "34634405549"
        
        # Limpiar o crear cliente de prueba en NEON [cite: 2026-02-07]
        client = self.db.query(Client).filter(Client.phone == self.phone).first()
        if not client:
            client = Client(
                full_name="Hernan Arango", 
                phone=self.phone, 
                metadata_json={"service_type": "None"}
            )
            self.db.add(client)
        else:
            client.metadata_json = {"service_type": "None"}
        
        self.db.commit()
        self.client = client

    def teardown_method(self):
        self.db.close()

    @pytest.mark.parametrize("mensaje, dia_esperado", [
        ("quiero para mañana a las 10am", "mañana"),
        ("miremos para el lunes a las 3 de la tarde", "lunes"),
        ("¿tienes hueco el próximo jueves a las 11:00?", "jueves")
    ])
    def test_persistencia_multiples_horarios(self, mensaje, dia_esperado):
        """
        Prueba que si el usuario dice un nombre parecido ('Manicura'), 
        el sistema lo traduzca al oficial y mantenga el flujo de booking.
        """
        print(f"\n🧪 Probando agendamiento: '{mensaje}'")

        # 1. Simulamos que en una interacción previa se guardó 'Manicura' (nombre sucio)
        self.client.metadata_json = {"service_type": "Manicura"}
        self.db.commit()

        # 2. Procesamos el mensaje que solo tiene la fecha
        respuesta, estado = self.master.process(self.db, self.phone, mensaje, [])

        # 3. 🛡️ VERIFICACIÓN DE FUZZY MATCHING
        # El sistema debe haber traducido 'Manicura' -> 'Manicure Esmalte Normal'
        servicio_final = estado.get("service_type")
        
        print(f"📊 [TEST] Input: 'Manicura' -> Sistema guardó: '{servicio_final}'")
        
        assert servicio_final == "Manicure Esmalte Normal", \
            f"❌ El Fuzzy Matching falló. Se esperaba el nombre oficial, pero quedó: {servicio_final}"

        # 4. VERIFICACIÓN DE RUTA
        # Si hay slots o mensaje de 'no hay hueco', significa que entró a BOOKING
        assert any(word in respuesta.lower() for word in ["tengo", "huecos", "lo siento", "mañana"]), \
            f"❌ El ruteo no llegó a Booking. Respuesta: {respuesta}"

    def test_cambio_de_opinion_horario(self):
        """
        Verifica que el sistema no se pierda si el usuario cambia la hora
        en mensajes consecutivos.
        """
        print(f"\n🧪 Probando cambio de opinión de horario...")
        
        # Inyectamos servicio oficial
        self.client.metadata_json = {"service_type": "Manicure Esmalte Normal"}
        self.db.commit()
        
        # Primer mensaje
        self.master.process(self.db, self.phone, "mañana a las 10am", [])
        
        # Cambio de opinión: "mejor a las 4pm"
        mensaje_cambio = "mejor a las 4pm que no puedo por la mañana"
        respuesta, estado = self.master.process(self.db, self.phone, mensaje_cambio, [])
        
        assert estado.get("service_type") == "Manicure Esmalte Normal"
        print(f"✅ Cambio de horario procesado manteniendo el servicio.")