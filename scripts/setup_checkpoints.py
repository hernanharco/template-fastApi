# scripts/setup_checkpoints.py
# Scrip para crear las tablas de langgraph checkpointer en Neon
import os
from dotenv import load_dotenv
from langgraph.checkpoint.postgres import PostgresSaver

load_dotenv()

def main():
    conn_string = os.getenv("DATABASE_URL")
    
    if not conn_string:
        print("❌ ERROR: DATABASE_URL no encontrada en .env")
        return
    
    # Mostrar info de conexión (ocultando contraseña)
    try:
        db_name = conn_string.split('/')[-1].split('?')[0]
        host = conn_string.split('@')[1].split('/')[0]
        print(f"🔗 Conectando a Neon: {host}/{db_name}")
    except:
        print(f"🔗 Conectando a Neon...")
    
    try:
        # 🟢 CORRECCIÓN: Usar 'with' (síncrono), NO 'async with'
        with PostgresSaver.from_conn_string(conn_string) as checkpointer:
            # setup() es síncrono también
            checkpointer.setup()
            
        print("✅ Tablas creadas exitosamente:")
        print("   - checkpoints")
        print("   - checkpoint_blobs")
        print("   - checkpoint_writes")
        print("   - checkpoint_migrations")
        print("\n🎉 ¡Listo! Ya puedes usar persistencia.")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Tips:")
        print("   1. Verifica que DATABASE_URL apunte a tu DB 'coreappointment', no 'neondb'")
        print("   2. Asegúrate de tener conexión a internet")
        print("   3. Verifica permisos de creación de tablas en Neon")

if __name__ == "__main__":
    main()  # 🟢 NO usar asyncio.run(), es código síncrono