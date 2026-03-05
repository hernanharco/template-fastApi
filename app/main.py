from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager # Requerido para el nuevo Lifespan
import uvicorn
import time
import os

from app.core.config import settings
from app.db.session import get_db, create_tables
from app.api.v1.api_route import api_router
from app.models.metrics import ApiRouteMetric
from app.db.session import SessionLocal

from fastapi import BackgroundTasks

# 2. Crea una función de ayuda fuera del middleware
def save_metric_task(path: str, method: str, status_code: int, process_time: float):
    db = SessionLocal()
    try:
        new_metric = ApiRouteMetric(
            path=path,
            method=method,
            status_code=status_code,
            process_time=process_time
        )
        db.add(new_metric)
        db.commit()
    except Exception as e:
        print(f"⚠️ Error guardando métricas en background: {e}")
    finally:
        db.close()

# 1. Definimos el ciclo de vida (Lifespan)
# Este reemplaza a @app.on_event("startup")
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 Starting FastAPI app in {settings.ENVIRONMENT} mode")

    # --- CONFIGURACIÓN DE LANGSMITH (TRACING) ---
    if settings.LANGSMITH_TRACING:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
        os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGSMITH_ENDPOINT or "https://api.smith.langchain.com"
        print("📊 LangSmith Tracing: ENABLED")
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"
        print("📊 LangSmith Tracing: DISABLED")
    # --------------------------------------------

    # --- VERIFICACIÓN DE ZONA HORARIA ---
    import pytz
    from datetime import datetime
    try:
        current_tz = pytz.timezone(settings.APP_TIMEZONE)
        local_time = datetime.now(current_tz)
        print(f"🌍 Timezone: {settings.APP_TIMEZONE}")
        print(f"🕒 Local Time: {local_time.strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(f"❌ Error configurando zona horaria: {e}")
    # ------------------------------------
    
    # En lugar de imprimir settings.DATABASE_URL completo:
    if settings.DATABASE_URL:
        print("🔗 Database URL: Configurada correctamente (Oculta por seguridad)")
    else:
        print("🔗 Database URL: No encontrada o incorrecta")
    # Aquí podrías conectar a Redis o cargar un modelo de IA pesado
    create_tables()

    yield  # <--- Aquí la app está encendida y recibiendo clientes
    
    # --- CIERRE (SHUTDOWN) ---
    print("👋 Iniciando proceso de apagado...")
    
    # Ejemplo 1: Cerrar todas las conexiones a la DB para no saturar a Neon
    from app.db.session import engine
    engine.dispose() 
    print("🔌 Conexiones a la base de datos cerradas.")
    
    # Ejemplo 2: Si tuvieras un sistema de logs en archivo, podrías cerrarlo
    print("💾 Logs guardados y archivos cerrados.")
    
    # Ejemplo 3: Limpiar memoria temporal
    print("🧹 Memoria temporal liberada.")
    
    print("✅ Apagado completo. ¡Hasta pronto!")

# 2. Inicializamos FastAPI con el lifespan
app = FastAPI(
    title=settings.TITLE_BACKEND,
    description=settings.TITLE_BACKEND + " application with " + settings.NAME_DATABASE + " integration",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan
)

# Revisa cual api esta consumiendo mas la base de datos
# 3. Modifica el Middleware
@app.middleware("http")
async def log_route_metrics(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    
    # 🚀 MAGIA: Usamos BackgroundTasks para no bloquear el flujo principal
    # Extraemos los datos necesarios antes para evitar problemas con el objeto request
    background_tasks = BackgroundTasks()
    background_tasks.add_task(
        save_metric_task, 
        request.url.path, 
        request.method, 
        response.status_code, 
        process_time
    )
    response.background = background_tasks
    
    return response

# 3. CORS Middleware dinámico
# Ahora toma la lista procesada desde tu Settings
app.add_middleware(
    CORSMiddleware,
    # 1. Usamos la propiedad que calcula la lista de dominios
    allow_origins=settings.allow_origins, 
    allow_credentials=True,
    # 2. Simplificamos la lógica de métodos
    # Si no es producción (es decir, desarrollo), permitimos todo "*"
    # Si es producción, limitamos a los métodos estándar
    allow_methods=["*"] if not settings.is_production else ["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# 4. Incluir router de API v1
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "message": settings.TITLE_BACKEND + " API is running",
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG
    }

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Endpoint de salud que verifica la conexión real a Neon de authCore
    """
    try:
        from sqlalchemy import text # Importante para SQLAlchemy 2.0
        db.execute(text("SELECT 1"))
        return {
            "status": "healthy" + " " + settings.TITLE_BACKEND,
            "environment": settings.ENVIRONMENT,
            "db_provider": settings.NAME_DATABASE,
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy" + " " + settings.TITLE_BACKEND,
            "environment": settings.ENVIRONMENT,
            "db_provider": settings.NAME_DATABASE,
            "database": "disconnected",
            "error": str(e)
        }

@app.get("/info")
async def app_info():
    return {
        "app_name": settings.TITLE_BACKEND,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "is_production": settings.is_production,
        "is_development": settings.ENVIRONMENT == "development"
    }

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level="debug" if settings.DEBUG else "info"
    )