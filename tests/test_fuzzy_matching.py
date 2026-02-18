import sys
from pathlib import Path
import pytest
from app.db.session import SessionLocal
from app.agents.main_master import ValeriaMaster
from app.models.clients import Client

# Aseguramos que Python encuentre la carpeta 'app'
ruta_proyecto = Path(__file__).parent.parent
sys.path.insert(0, str(ruta_proyecto))

class TestFuzzyLogicPremium:
    """
    Test de Excelencia: Valida la limpieza de datos y persistencia en NEON.
    Ajustado para mantener un equilibrio entre flexibilidad y precisión. [cite: 2026-02-18]
    """

    def setup_method(self):
        self.master = ValeriaMaster()
        self.db = SessionLocal()
        self.phone = "34634405549"
        
        # Limpiamos el estado del cliente con SRP
        client = self.db.query(Client).filter(Client.phone == self.phone).first()
        if client:
            client.metadata_json = {"service_type": None, "messages": []}
            self.db.commit()
        self.client = client

    def teardown_method(self):
        self.db.close()

    @pytest.mark.parametrize("nombre_sucio, nombre_oficial_esperado", [
        # Ajustado: Mapeos directos por similitud fonética/escritura             
        ("corte cabello", "Corte de Cabello"),
        ("cejas", "Cejas"),
        ("quiero info", None), 
    ])
    def test_robustez_similitud_premium(self, nombre_sucio, nombre_oficial_esperado):
        """
        Verifica que el sistema limpie el nombre del servicio antes de procesar. [cite: 2026-01-30]
        """
        print(f"\n🧪 Validando servicio: '{nombre_sucio}'")

        # 1. Inyectamos el servicio en el estado (JSONB en NEON) [cite: 2026-02-18]
        self.client.metadata_json = {"service_type": nombre_sucio}
        self.db.commit()

        # 2. El usuario interactúa
        self.master.process(self.db, self.phone, "disponibilidad para mañana", [])

        # 3. Verificamos la limpieza en el estado devuelto
        # Refrescamos desde la DB para asegurar aislamiento físico [cite: 2026-02-18]
        self.db.refresh(self.client)
        servicio_final = self.client.metadata_json.get("service_type")

        if nombre_oficial_esperado:
            print(f"✅ Resultado en NEON: '{servicio_final}'")
            assert servicio_final == nombre_oficial_esperado
        else:
            # No debe haber hecho match con servicios comunes si es muy ambiguo
            assert servicio_final == nombre_sucio or servicio_final is None

    def test_persistencia_real_en_neon(self):
        """
        SRP: Validar que el objeto de sesión persiste el cambio en el JSONB. [cite: 2026-02-13, 2026-02-18]
        """
        input_sucio = "pedicura semi"
        self.client.metadata_json = {"service_type": input_sucio}
        self.db.commit()

        # Disparamos el motor de Valeria
        self.master.process(self.db, self.phone, "mañana a las 10am", [])

        # Consultamos el estado físico final
        self.db.refresh(self.client)
        valor_db = self.client.metadata_json.get("service_type")
        
        print(f"💾 Persistencia NEON: '{input_sucio}' -> '{valor_db}'")
        assert valor_db == "Pedicure Semi Permanente"