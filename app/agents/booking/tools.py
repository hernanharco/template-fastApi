import logging
from datetime import date
from sqlalchemy import text
from app.db.session import SessionLocal
from app.services.booking_scheduler import get_booking_options_with_favorites, confirm_booking_option

logger = logging.getLogger(__name__)

def search_slots_tool(client_phone: str, service_id: int, target_date: str = None):
    """
    🎯 SRP: Buscar disponibilidad técnica en la DB.
    """
    db = SessionLocal()
    try:
        # Validación robusta de fecha
        try:
            parsed_date = date.fromisoformat(target_date) if target_date else date.today()
        except (ValueError, TypeError):
            parsed_date = date.today()
            logger.warning(f"⚠️ Fecha inválida recibida: {target_date}. Usando hoy.")

        result = get_booking_options_with_favorites(db, client_phone, service_id, parsed_date)
        return result
    except Exception as e:
        logger.error(f"❌ Error en search_slots_tool: {e}")
        return {"success": False, "options": [], "error": str(e)}
    finally:
        db.close()

def find_service_by_name(search_text: str):
    """
    🎯 SRP: Traducir texto del usuario a un ID de servicio real.
    """
    db = SessionLocal()
    try:
        # Usamos ILIKE para que 'cejas' encuentre 'Cejas' o 'CEJAS'
        query = text("""
            SELECT id, name FROM services 
            WHERE name ILIKE :search AND is_active = true 
            LIMIT 1
        """)
        result = db.execute(query, {"search": f"%{search_text}%"}).first()
        return {"id": result[0], "name": result[1]} if result else None
    finally:
        db.close()

def book_appointment_tool(client_phone: str, service_id: int, colab_id: int, dt_str: str):
    """
    🎯 SRP: Confirmar y escribir la cita en la tabla 'appointments'.
    """
    db = SessionLocal()
    try:
        # selected_datetime viene como "YYYY-MM-DD HH:MM"
        return confirm_booking_option(db, client_phone, service_id, colab_id, dt_str)
    except Exception as e:
        logger.error(f"❌ Error al confirmar cita: {e}")
        return {"success": False, "message": "Error interno al reservar."}
    finally:
        db.close()