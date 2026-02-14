import sys
from pathlib import Path
from dotenv import load_dotenv

# Configuración de rutas
ruta_proyecto = Path(__file__).parent.parent
load_dotenv(ruta_proyecto / ".env")
sys.path.insert(0, str(ruta_proyecto))

from app.db.session import SessionLocal
from app.services.appointment_service import AppointmentService

def test_logic_by_department():
    db = SessionLocal()
    print(f"\n{'='*20} 🏁 TEST DE FILTRADO FINAL {'='*20}")
    
    try:
        # PRUEBA 1: Servicio de Uñas (Dept 2)
        # Usamos el ID 1 que vimos en tu JSON (Uñas Normales)
        print("\n💅 Caso 1: Cliente pide 'Uñas Normales' (Dept 2)")
        colabs_uñas = AppointmentService.get_eligible_collaborators(db, 1)
        nombres_uñas = [c.name for c in colabs_uñas]
        print(f"👉 Resultado esperado: ['Elianac']")
        print(f"🔍 Resultado DB: {nombres_uñas}")

        # PRUEBA 2: Servicio de Cabello (Dept 3)
        # Usamos el ID 2 que movimos al Dept 3 (Corte de Cabello)
        print("\n💇‍♂️ Caso 2: Cliente pide 'Corte de Cabello' (Dept 3)")
        colabs_hair = AppointmentService.get_eligible_collaborators(db, 2)
        nombres_hair = [c.name for c in colabs_hair]
        print(f"👉 Resultado esperado: ['Elianac', 'Hernanc']")
        print(f"🔍 Resultado DB: {nombres_hair}")

        print(f"\n{'='*55}")
        if "Elianac" in nombres_uñas and len(nombres_uñas) == 1:
            if "Hernanc" in nombres_hair and "Elianac" in nombres_hair:
                print("🏆 ¡PERFECTO! La lógica vertical funciona al 100%.")
    
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_logic_by_department()