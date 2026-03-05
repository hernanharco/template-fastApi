# app/db/session.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
# 🟢 Importaciones necesarias para asíncrono
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings
from app.models.base import Base

# ==============================================================================
# --- CONFIGURACIÓN SÍNCRONA (Para FastAPI tradicional) ---
# ==============================================================================
# 'create_engine' funciona bien con la URL tal cual viene del .env
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True, 
    pool_recycle=300, 
    pool_size=5, 
    max_overflow=5,
    pool_timeout=30,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Generador síncrono para dependencias de FastAPI (@app.get)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==============================================================================
# --- 🟢 CONFIGURACIÓN ASÍNCRONA (Para Agentes LangGraph) ---
# ==============================================================================

# 1. Aseguramos que la URL comience con postgresql+asyncpg y limpiamos parámetros
# para pasarlos explícitamente en 'connect_args'.
base_url = settings.DATABASE_URL.split("?")[0]
async_url = base_url.replace("postgresql://", "postgresql+asyncpg://")

# 2. Creamos el engine forzando el driver asyncpg y configurando SSL
async_engine = create_async_engine(
    async_url,
    # 🟢 Pasamos SSL y Channel Binding aquí para asyncpg
    connect_args={
        "ssl": "require",
        "server_settings": {"channel_binding": "require"}
    },
    echo=False
)

# 🟢 AsyncSessionLocal es la que debes usar en tools.py con 'async with'
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ==============================================================================
# --- UTILIDADES ---
# ==============================================================================
def create_tables():
    """Verifica conexión y crea tablas síncronamente al iniciar"""
    print(f"--- Verificando conexión a NEON ({settings.ENVIRONMENT}) ---")
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        Base.metadata.create_all(bind=engine)
        print("✅ Conexión exitosa: Tablas verificadas/creadas en NEON.")
        
    except OperationalError as e:
        print("\n" + "!"*60)
        print("⚠️  AVISO DE CONFIGURACIÓN DE BASE DE DATOS")
        print(f"No se pudo conectar a la base de datos en: {settings.ENVIRONMENT}")
        print("MENSAJE DEL SISTEMA: Revisa que la URL en tu archivo .env sea la correcta.")
        print("El programa continuará ejecutándose, pero las consultas fallarán.")
        print("!"*60 + "\n")
        
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado al inicializar la DB: {e}")

def drop_tables():
    """Borra tablas síncronamente"""
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception as e:
        print(f"No se pudieron borrar las tablas: {e}")