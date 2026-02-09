from app.agents.booking_agent import run_booking_agent
from dotenv import load_dotenv

load_dotenv()

print("--- 🤖 Asistente de Citas Activo (Escribe 'salir' para terminar) ---")

while True:
    pregunta = input("\nUsuario: ")
    if pregunta.lower() in ["salir", "exit", "quit"]:
        print("Adiós!")
        break
    
    respuesta = run_booking_agent(pregunta)
    print(f"\nIA: {respuesta}")