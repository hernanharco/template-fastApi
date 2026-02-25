from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError  # Importante para capturar fallos de red/auth

from app.core.settings import settings

# Importamos declarative_base desde el modelo base
from app.models.base import Base

# 1. Creamos el engine
# --- CONFIGURACIÓN DEL ENGINE PARA NEON (AHORRO DE CU) ---
engine = create_engine(
    settings.DATABASE_URL,
    # 1. Verifica si la conexión sigue viva antes de usarla
    pool_pre_ping=True, 
    
    # 2. Reinicia las conexiones cada 5 min (300s)
    # Evita que conexiones viejas mantengan a Neon despierto
    pool_recycle=300, 
    
    # 3. Mantiene máximo 5 conexiones abiertas. Ideal para SaaS pequeño.
    pool_size=5, 
    
    # 4. No permite crear conexiones extra fuera de las 5 del pool.
    # Así controlas exactamente cuánta carga le das a Neon.
    max_overflow=5,
    
    # 5. Tiempo máximo de espera para obtener una conexión del pool
    pool_timeout=30,

    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """
    Intenta crear las tablas, pero si la URL es incorrecta o no hay conexión,
    muestra un mensaje en lugar de detener el servidor.
    """
    print(f"--- Verificando conexión a NEON ({settings.ENVIRONMENT}) ---")
    try:
        # Intentamos una operación mínima: pedir la versión o un SELECT 1
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        # Si llega aquí, la conexión es real. Creamos las tablas.
        Base.metadata.create_all(bind=engine)
        print("✅ Conexión exitosa: Tablas verificadas/creadas en NEON.")
        
    except OperationalError as e:
        # Aquí capturamos el error de "password authentication failed" o "host not found"
        print("\n" + "!"*60)
        print("⚠️  AVISO DE CONFIGURACIÓN DE BASE DE DATOS")
        print(f"No se pudo conectar a la base de datos en: {settings.ENVIRONMENT}")
        print("MENSAJE DEL SISTEMA: Revisa que la URL en tu archivo .env sea la correcta.")
        print("El programa continuará ejecutándose, pero las consultas fallarán.")
        print("!"*60 + "\n")
        
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado al inicializar la DB: {e}")

def drop_tables():
    """Solo se ejecuta si realmente hay conexión"""
    try:
        Base.metadata.drop_all(bind=engine)
    except Exception as e:
        print(f"No se pudieron borrar las tablas: {e}")