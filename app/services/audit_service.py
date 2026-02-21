from sqlalchemy.orm import Session
from app.models.audit_log import AIAuditLog

class AuditService:
    """
    SRP: Gestionar la creación de registros de auditoría sin mezclar lógica de negocio.
    """
    
    @staticmethod
    def register_interaction(
        db: Session,
        phone: str,
        message: str,
        intent: str,
        response: str,
        state_before: dict,
        state_after: dict
    ):
        try:
            log_entry = AIAuditLog(
                phone_number=phone,
                user_message=message,
                detected_intent=intent,
                detected_service=state_after.get("service_type"),
                final_response=response,
                state_before=state_before,
                state_after=state_after
            )
            db.add(log_entry)
            db.commit()
            print(f"📝 [AUDIT] Interacción de {phone} guardada en NEON.")
        except Exception as e:
            db.rollback()
            print(f"❌ [AUDIT] No se pudo guardar el log: {e}")