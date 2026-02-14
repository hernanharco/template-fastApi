import sys
from pathlib import Path
from dotenv import load_dotenv

# Configuración de rutas
ruta_proyecto = Path(__file__).parent.parent
load_dotenv(ruta_proyecto / ".env")
sys.path.insert(0, str(ruta_proyecto))

from app.db.session import SessionLocal
from app.services.appointment_service import AppointmentService
from app.models.services import Service

def test_service_filtering():
    print(f"\n{'='*20} 🚀 PROBANDO APPOINTMENT SERVICE {'='*20}")
    db = SessionLocal()
    
    try:
        # 1. Buscamos un servicio que sepamos que existe (ej: uno de uñas)
        # Si no sabes el ID, buscamos el primero que diga 'Manicura'
        service = db.query(Service).filter(Service.name.ilike("%manicura%")).first()
        
        if not service:
            # Si no hay, agarramos el primero de la lista
            service = db.query(Service).first()

        if service:
            print(f"🔍 Buscando colaboradores para el servicio: '{service.name}' (ID: {service.id})")
            
            # 2. LLAMAMOS A TU NUEVA CLASE
            colaboradores = AppointmentService.get_eligible_collaborators(db, service.id)
            
            if colaboradores:
                print(f"✅ ¡Éxito! Se encontraron {len(colaboradores)} colaboradores aptos:")
                for c in colaboradores:
                    print(f"   - 👤 {c.name}")
            else:
                print(f"⚠️ No se encontraron colaboradores vinculados al departamento del servicio '{service.name}'.")
        else:
            print("❌ No hay servicios en la base de datos para realizar la prueba.")

    except Exception as e:
        print(f"❌ Error durante la prueba: {e}")
    finally:
        db.close()
        print(f"{'='*56}\n")

if __name__ == "__main__":
    test_service_filtering()