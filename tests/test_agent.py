import sys
import os
from dotenv import load_dotenv

# 1. Carga de entorno y PATH
load_dotenv()
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.clients import Client
# Asumimos que 'maria' es tu instancia que envuelve al grafo compilado
from app.agents.core.maria_master import maria 
from rich import print
from rich.console import Console
from langchain_core.messages import HumanMessage

console = Console()

def run_test():
    db: Session = SessionLocal()
    console.print("[bold cyan]--- 📱 Sistema MariaMaster (LangGraph + Neon) ---[/bold cyan]")
    
    try:
        # A. Identificación
        phone = input("Introduce número de móvil (ej: 34600111222): ").strip()
        if not phone:
            console.print("[bold red]❌ Error: Debes introducir un número.[/bold red]")
            return

        # B. Limpieza de memoria (Neon Metadata)
        clean = input("¿Deseas resetear la memoria en Neon? (s/n): ").lower()
        if clean == 's':
            cliente = db.query(Client).filter(Client.phone == phone).first()
            if cliente:
                # 1. Limpiamos mensajes
                cliente.metadata_json = {"messages": []}
                # 2. FIX: No usamos None para evitar el error de base de datos.
                # Ponemos un valor temporal que obligue a Maria a preguntar.
                cliente.full_name = "Usuario Nuevo" 
                db.commit()
                console.print(f"[green]✅ Memoria reseteada para {phone}[/green]")

        console.print(f"\n[bold yellow]Conectado como: {phone}.[/bold yellow]")
        console.print("[dim]Escribe 'salir' para terminar o 'estado' para ver el State actual.[/dim]")

        # C. Bucle de conversación
        while True:
            user_input = input("\n👤 Tú: ").strip()
            
            if user_input.lower() in ["salir", "exit", "quit"]:
                break
            
            if not user_input:
                continue

            try:
                # 🚀 PROCESAMIENTO
                # Pasamos el db session y el teléfono. 
                # Tu clase Maria debe usar el teléfono como thread_id internamente.
                respuesta_maria = maria.process(db, phone, user_input)
                
                # Mostramos la respuesta con estilo
                print(f"\n🤖 [bold magenta]Maria:[/bold magenta] {respuesta_maria}")
            
            except Exception as e:
                console.print(f"\n[bold red]❌ Error en el procesamiento:[/bold red] {e}")
                import traceback
                traceback.print_exc()

    finally:
        db.close()
        console.print("\n[blue]🔌 Conexión a Neon cerrada. ¡Prueba terminada![/blue]")

if __name__ == "__main__":
    run_test()