# app/db/base.py
from app.models.base import Base  # Tu Base original
from app.db.session import engine # Importamos el motor

# --- IMPORTACIÓN DE TODOS LOS MODELOS ---
# Importarlos aquí es lo que permite que Base.metadata los "vea"
from app.models.appointments import Appointment, AppointmentStatus
from app.models.reminder import ScheduledReminder
from app.models.clients import Client
from app.models.collaborators import Collaborator
from app.models.services import Service
from app.models.business_hours import BusinessHours # Faltaba este
from app.models.departments import Department      # Faltaba este
from app.models.audit_log import AIAuditLog          # Faltaba este
# Si tienes más como metrics.py o learning.py, impórtalos también aquí

def create_tables():
    """
    Función que crea todas las tablas en Neon.
    Se llama desde el setup.sh
    """
    print("✨ Creando tablas en Neon si no existen...")
    # Base.metadata busca todos los modelos cargados en memoria (por eso los importamos arriba)
    Base.metadata.create_all(bind=engine)
    print("✅ Todas las tablas (Citas, Recordatorios, Horarios, etc.) sincronizadas correctamente.")