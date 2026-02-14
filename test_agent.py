import os
from dotenv import load_dotenv
load_dotenv()

from app.db.session import SessionLocal
from app.agents.main_master import ValeriaMaster
from app.models.clients import Client
from sqlalchemy.orm.attributes import flag_modified


def run_test():
    orch    = ValeriaMaster()
    db      = SessionLocal()
    history = []

    print("--- 📱 Sistema Real CoreAppointment (Con Memoria) ---")
    phone = input("Introduce número de móvil: ")

    # --- 🧹 RESET COMPLETO PARA DESARROLLO ---
    reset = input("¿Deseas limpiar la memoria de este cliente para empezar de cero? (s/n): ")
    if reset.lower() == 's':
        cliente = db.query(Client).filter(Client.phone == phone).first()
        if cliente:
            cliente.current_service_id = None
            # ✅ Limpiamos TODO el metadata_json — no solo last_interaction
            cliente.metadata_json = {}
            flag_modified(cliente, "metadata_json")
            db.commit()
            print(f"✅ Memoria limpiada en Neon para {phone}.")
        else:
            print("⚠️ Cliente no encontrado, se creará uno nuevo al hablar.")

    try:
        while True:
            msg = input("\n👤 Tú: ")

            if not msg.strip(): continue
            if msg.lower() in ["salir", "exit"]: break

            respuesta, history = orch.process(db, phone, msg, history)
            print(f"🤖 Valeria: {respuesta}")

    except Exception as e:
        print(f"❌ Error durante el test: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        db.close()
        print("\n--- 🔌 Conexión con Neon cerrada ---")


if __name__ == "__main__":
    run_test()