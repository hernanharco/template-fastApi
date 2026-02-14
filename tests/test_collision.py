import sys
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Configuración de rutas
ruta_proyecto = Path(__file__).parent.parent
load_dotenv(ruta_proyecto / ".env")
sys.path.insert(0, str(ruta_proyecto))

from app.db.session import SessionLocal
from app.models.appointments import Appointment
from app.services.appointment_service import AppointmentService

def simulate_collision():
    db = SessionLocal()
    print(f"\n{'='*20} 🛡️ TEST DE COLISIÓN DE HORARIOS {'='*20}")
    
    try:
        # --- CONFIGURACIÓN DEL ESCENARIO ---
        # 1. Definimos una hora: Mañana a las 10:00 AM
        hora_test = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        # 2. SIMULAMOS: Elianac (ID 8) ya tiene una cita de Uñas a esa hora
        test_appointment = Appointment(
            client_id=1,
            service_id=1,
            collaborator_id=8,
            client_name="Cliente de Prueba",  # <-- Añade esto
            client_phone="123456789",         # <-- Añade esto (si es NOT NULL)
            client_email="test@example.com",  # <-- Añade esto
            start_time=hora_test,
            end_time=hora_test + timedelta(minutes=30),
            status="CONFIRMED"                # Asegúrate que coincida con el status del error
        )
        db.add(test_appointment)
        db.commit()
        print(f"📌 ESCENARIO: Elianac tiene cita de Uñas a las {hora_test.strftime('%H:%M')}")

        # --- LA PRUEBA DE FUEGO ---
        # 3. Alguien pide "Corte de Cabello" (ID 2) a la misma hora
        print(f"🔍 Cliente pide 'Corte de Cabello' (Dept 3) a las {hora_test.strftime('%H:%M')}...")
        
        # Llamamos al método que actualizamos en el paso anterior
        disponibles = AppointmentService.get_available_collaborators(db, service_id=2, start_time=hora_test)
        
        nombres = [c.name for c in disponibles]
        print(f"✅ Colaboradores encontrados: {nombres}")

        # --- VALIDACIÓN ---
        if "Hernanc" in nombres and "Elianac" not in nombres:
            print("\n🏆 ¡PRUEBA SUPERADA!")
            print("Resultado: Elianac está ocupada en Uñas, así que el sistema solo ofrece a Hernanc.")
        else:
            print("\n❌ FALLO: Eliana no debería aparecer si ya tiene una cita.")

        # Limpieza: Borramos la cita de prueba para no ensuciar Neon
        db.delete(test_appointment)
        db.commit()

    except Exception as e:
        print(f"❌ Error en el test: {e}")
        db.rollback()
    finally:
        db.close()
        print(f"{'='*60}\n")

if __name__ == "__main__":
    simulate_collision()