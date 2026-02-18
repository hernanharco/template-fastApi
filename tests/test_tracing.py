import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 1. Configuración de rutas (Basado en tu test_real.py exitoso)
ruta_proyecto = Path(__file__).parent.parent
load_dotenv(ruta_proyecto / ".env")
sys.path.insert(0, str(ruta_proyecto))

from app.db.session import SessionLocal
# Cambiado a main_master según tu estructura de archivos reciente
from app.agents.main_master import ValeriaMaster 
from app.models.clients import Client
from sqlalchemy.orm.attributes import flag_modified

def trigger_test():
    # Corregido: El error de las comillas en el f-string
    print(f"\n{'-'*20} 🚀 DISPARANDO TRAZA A LANGSMITH {'-'*20}")
    
    db = SessionLocal()
    master = ValeriaMaster()
    
    # Usamos el teléfono verificado
    PHONE_TEST = "34634405549" 

    try:
        # Aseguramos existencia del cliente para evitar el error 'NoneType'
        cliente = db.query(Client).filter(Client.phone == PHONE_TEST).first()
        if not cliente:
            print(f"🛰️ Creando cliente para pruebas en NEON...")
            cliente = Client(full_name="Hernan Arango", phone=PHONE_TEST, metadata_json={})
            db.add(cliente)
            db.commit()
            db.refresh(cliente)

        # 2. Paso clave para el test: 
        # Si queremos probar "en la tarde", primero debemos asegurar que en Neon 
        # ya exista una fecha (ej. mañana) para ver si Valeria la mantiene.
        from datetime import datetime, timedelta
        mañana = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        print(f"📝 Seteando fecha previa en DB: {mañana}")
        cliente.metadata_json = {"appointment_date": mañana}
        flag_modified(cliente, "metadata_json")
        db.commit()

        # 3. Simulación del mensaje
        print(f"📡 Enviando mensaje: 'en la tarde por fa'")
        
        # El history vacío simula el inicio de un nuevo turno de mensaje
        respuesta, history = master.process(
            db, 
            PHONE_TEST, 
            "en la tarde por fa", 
            []
        )

        print(f"\n✅ Respuesta de Valeria: {respuesta[:120]}...")
        
        # 4. Verificación de persistencia en NEON (Aislamiento Físico)
        db.refresh(cliente)
        print(f"📋 Metadata final en Neon: {cliente.metadata_json}")

    except Exception as e:
        print(f"❌ Error durante el rastreo: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()
        print(f"{'-'*60}\n")

if __name__ == "__main__":
    trigger_test()