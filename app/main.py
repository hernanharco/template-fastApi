from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager # Requerido para el nuevo Lifespan
import uvicorn

from app.core.settings import settings
from app.db.session import get_db, create_tables

# 1. Definimos el ciclo de vida (Lifespan)
# Este reemplaza a @app.on_event("startup")
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 Starting FastAPI app in {settings.environment} mode")
    
    # En lugar de imprimir settings.database_url completo:
    if settings.database_url:
        print("🔗 Database URL: Configurada correctamente (Oculta por seguridad)")
    else:
        print("🔗 Database URL: No encontrada o incorrecta")
    # Aquí podrías conectar a Redis o cargar un modelo de IA pesado
    create_tables()
    
    yield  # <--- Aquí la app está encendida y recibiendo clientes
    
    # --- CIERRE (SHUTDOWN) ---
    print("👋 Iniciando proceso de apagado...")
    
    # Ejemplo 1: Cerrar todas las conexiones a la DB para no saturar a Neon
    from .db.session import engine
    engine.dispose() 
    print("🔌 Conexiones a la base de datos cerradas.")
    
    # Ejemplo 2: Si tuvieras un sistema de logs en archivo, podrías cerrarlo
    print("💾 Logs guardados y archivos cerrados.")
    
    # Ejemplo 3: Limpiar memoria temporal
    print("🧹 Memoria temporal liberada.")
    
    print("✅ Apagado completo. ¡Hasta pronto!")

# 2. Inicializamos FastAPI con el lifespan
app = FastAPI(
    title="AuthCore API",
    description="FastAPI application with Neon PostgreSQL integration",
    version="1.0.0",
    debug=settings.debug,
    lifespan=lifespan
)

# 3. CORS Middleware dinámico
# Ahora toma la lista procesada desde tu Settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allow_origins,
    allow_credentials=True,
    allow_methods=["*"] if settings.is_development else ["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "AuthCore API is running",
        "environment": settings.environment,
        "debug": settings.debug
    }

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Endpoint de salud que verifica la conexión real a Neon
    """
    try:
        from sqlalchemy import text # Importante para SQLAlchemy 2.0
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "environment": settings.environment,
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "environment": settings.environment,
            "database": "disconnected",
            "error": str(e)
        }

@app.get("/info")
async def app_info():
    return {
        "app_name": "AuthCore API",
        "version": "1.0.0",
        "environment": settings.environment,
        "debug": settings.debug,
        "is_production": settings.is_production,
        "is_development": settings.is_development
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level="debug" if settings.debug else "info"
    )