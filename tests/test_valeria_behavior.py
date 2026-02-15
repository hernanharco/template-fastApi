import sys
import os
# Añadimos el path para poder importar app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.agents.main_master import ValeriaMaster
from app.models.clients import Client

# Colores para la terminal
GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"

class AgentBehaviorTest:
    def __init__(self):
        self.master = ValeriaMaster()
        self.db: Session = SessionLocal()
        self.test_phone = "999888777" # Número exclusivo para pruebas

    def setup_test_client(self, name="Usuario"):
        """Limpia y prepara el cliente de prueba"""
        client = self.db.query(Client).filter(Client.phone == self.test_phone).first()
        if client:
            self.db.delete(client)
            self.db.commit()
        print(f"{BLUE}--- 🧹 Entorno de prueba limpio ---{RESET}")

    def run_case(self, description, messages):
        """Ejecuta una secuencia de mensajes y evalúa el comportamiento"""
        print(f"\n🚀 {BLUE}TEST: {description}{RESET}")
        history = []
        
        for msg in messages:
            print(f"👤 Usuario: {msg}")
            response, history = self.master.process(self.db, self.test_phone, msg, history)
            print(f"🤖 Valeria: {response}")
        
        return response, history

    def assert_contains(self, text, keyword, case_name):
        """Verifica si la respuesta contiene lo esperado"""
        if keyword.lower() in text.lower():
            print(f"✅ {GREEN}PASÓ: {case_name}{RESET}")
        else:
            print(f"❌ {RED}FALLÓ: {case_name} (No se encontró '{keyword}'){RESET}")

# --- EJECUCIÓN DE LAS PRUEBAS ---

if __name__ == "__main__":
    tester = AgentBehaviorTest()

    # CASO 1: Flujo de Identidad (Usuario Nuevo)
    tester.setup_test_client()
    resp, _ = tester.run_case("Identificación de nuevo cliente", ["Hola"])
    tester.assert_contains(resp, "nombre", "Preguntar nombre a desconocido")

    # CASO 2: Cambio de opinión
    tester.run_case("Cambio de servicio a mitad de flujo", [
        "Soy Hernan",
        "Quiero unas uñas normales",
        "No, mejor quiero otra cosa"
    ])
    # Aquí verificamos que el Master haya limpiado el estado
    client = tester.db.query(Client).filter(Client.phone == tester.test_phone).first()
    if client.current_service_id is None:
        print(f"✅ {GREEN}PASÓ: Limpieza de estado por cambio de opinión{RESET}")
    else:
        print(f"❌ {RED}FALLÓ: No se limpió el servicio tras pedir 'otra cosa'{RESET}")

    # CASO 3: Cierre de cita exitoso
    resp, _ = tester.run_case("Cita completa y despedida", [
        "Hola, soy Hernan",          # <--- Primero se presenta
        "uñas acrilicas", 
        "el lunes", 
        "a las 14:30", 
        "gracias"
    ])
    tester.assert_contains(resp, "lindo día", "Despedida cordial post-cita")