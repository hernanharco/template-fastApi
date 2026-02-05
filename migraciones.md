
# Dentro de la carpeta de tu backend
pip install alembic psycopg2-binary

# Usamos pnpm para correr el comando si lo tienes mapeado, o directo en la terminal
alembic init migrations

# Editar el archivo migrations/env.py para que lea la URL de la base de datos desde el .env
# y que use postgresql:// en lugar de postgres://
```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os # <-- Necesario para leer el sistema
from dotenv import load_dotenv # <-- Necesario para leer el .env

# --- IMPORTACIONES PARA TU PROYECTO ---
from app.models.base import Base 
import app.models.services
import app.models.business_hours
# --------------------------------------

load_dotenv() # <-- Cargamos tu .env actual

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata 

def run_migrations_offline() -> None:
    # Para modo offline, también leemos del .env
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
    # CAPTURAMOS LA URL DEL .ENV
    db_url = os.getenv("DATABASE_URL")
    
    # IMPORTANTE: SQLAlchemy necesita 'postgresql://', no 'postgres://'
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    # Creamos la configuración dinámica
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = db_url # <-- Aquí sucede la magia

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

# Generar el archivo de migración
alembic revision --autogenerate -m "create services and business hours tables"

# Aplicar los cambios a Neon
alembic upgrade head