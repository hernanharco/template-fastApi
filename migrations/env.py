import sys
import os
import pkgutil # <--- 1. Asegúrate de importar esto
from pathlib import Path
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# --- 🛠️ CONFIGURACIÓN DEL PATH ---
root_path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_path))

# --- 📦 IMPORTACIONES AUTOMÁTICAS DE MODELOS ---
from app.models.base import Base 
import app.models as models # Importamos el paquete de modelos

# 2. Este bucle busca CUALQUIER archivo .py en app/models y lo importa
# Esto registra automáticamente AIAuditLog, Appointment, Client, etc., en la Base.
for loader, module_name, is_pkg in pkgutil.walk_packages(models.__path__, models.__name__ + "."):
    __import__(module_name)

# 3. Ahora target_metadata contiene TODAS las tablas detectadas automáticamente
target_metadata = Base.metadata 
# -----------------------------------------------

load_dotenv()

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

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
    """Ejecutar migraciones en modo 'online'."""
    db_url = os.getenv("DATABASE_URL")
    
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