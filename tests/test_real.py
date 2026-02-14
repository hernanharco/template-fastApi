import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 1. Configuramos rutas y entorno
ruta_proyecto = Path(__file__).parent.parent
load_dotenv(ruta_proyecto / ".env")
sys.path.insert(0, str(ruta_proyecto))

import pytest
from app.db.session import SessionLocal
from app.models.clients import Client

def test_conexion_real_neon():
    print(f"\n{'-'*20} 🚀 INICIANDO TEST REAL EN NEON {'-'*20}")
    db = SessionLocal()
    
    try:
        # Datos de prueba
        PHONE_TEST = "999888777"
        NAME_TEST = "Hernan Test"
        
        # 2. Limpieza (Borramos si ya existe de un error previo)
        db.query(Client).filter(Client.phone == PHONE_TEST).delete()
        db.commit()

        # 3. CREACIÓN (Usando los nombres de columna correctos: full_name)
        print(f"🛰️ Enviando datos a Neon para {NAME_TEST}...")
        nuevo_cliente = Client(
            full_name=NAME_TEST, 
            phone=PHONE_TEST,
            source="ia_test",
            metadata_json={"test_date": "2026-02-14"} # Probando tu JSONB
        )
        
        db.add(nuevo_cliente)
        db.commit()
        
        # 4. VERIFICACIÓN (¿De verdad está ahí?)
        cliente_db = db.query(Client).filter(Client.phone == PHONE_TEST).first()
        
        assert cliente_db is not None
        assert cliente_db.full_name == NAME_TEST
        print(f"✅ ¡Éxito! Cliente guardado y recuperado de Neon.")
        print(f"📋 Datos en JSONB: {cliente_db.metadata_json}")

        # 5. LIMPIEZA FINAL
        db.delete(cliente_db)
        db.commit()
        print(f"🧹 Base de datos limpia tras el test.")

    except Exception as e:
        print(f"❌ Error durante la integración: {e}")
        db.rollback() # Si algo falla, deshacemos cambios
    finally:
        db.close()
        print(f"{'-'*60}\n")

if __name__ == "__main__":
    test_conexion_real_neon()