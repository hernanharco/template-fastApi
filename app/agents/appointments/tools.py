import logging
from datetime import date
from app.db.session import SessionLocal
from app.services.booking_scheduler import get_booking_options_with_favorites, confirm_booking_option

logger = logging.getLogger(__name__)

def search_slots_tool(client_phone: str, service_id: int, target_date_str: str = None):
    """
    🎯 SRP: Buscar disponibilidad técnica usando el scheduler.
    """
    db = SessionLocal()
    try:
        # El scheduler espera un objeto date, no un string
        parsed_date = date.fromisoformat(target_date_str) if target_date_str else date.today()
        return get_booking_options_with_favorites(db, client_phone, service_id, parsed_date)
    except Exception as e:
        logger.error(f"❌ Error buscando slots: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()

async def book_appointment_tool(client_phone: str, service_id: int, colab_id: int, dt_str: str):
    """
    🎯 SRP: Ejecutar la confirmación final de la cita.
    """
    db = SessionLocal()
    try:
        # Llamamos a tu service async que maneja el link de Telegram y el AppointmentManager
        return await confirm_booking_option(db, client_phone, service_id, colab_id, dt_str)
    except Exception as e:
        logger.error(f"❌ Error confirmando cita: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()