import sys
from pathlib import Path
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
from dotenv import load_dotenv

# --- 🛠️ CONFIGURACIÓN DEL PATH (Añadido para evitar ModuleNotFoundError) ---
# Esto permite que Alembic encuentre la carpeta 'app' desde cualquier lugar
root_path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_path))

# --- 📦 IMPORTACIONES DE TU PROYECTO ---
# Ahora sí podemos importar la Base y los modelos sin errores
from app.models.base import Base 
import app.models.services
import app.models.business_hours
import app.models.collaborators
import app.models.learning  # <--- Tu nuevo modelo de aprendizaje
# --------------------------------------

load_dotenv()

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic usará esta metadata para comparar la DB con tus modelos de Python
target_metadata = Base.metadata 

def run_migrations_offline() -> None:
    """Ejecutar migraciones en modo 'offline'."""
    url = os.getenv("DATABASE_URL")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Ejecutar migraciones en modo 'online' (conectado a Neon)."""
    db_url = os.getenv("DATABASE_URL")
    
    # Corrección para compatibilidad con SQLAlchemy 2.0+
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = db_url 

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()