from sqlalchemy.orm import Session
from app.models.services import Service 

class ServiceOrchestrator:
    """
    SRP: Responsable exclusivamente de consultar y formatear 
    la información del catálogo de servicios desde NEON.
    """

    def get_catalog_summary(self, db: Session) -> str:
        """
        Consulta la tabla de servicios y devuelve un resumen visual.
        Se usa tanto en saludos como en consultas directas.
        """
        try:
            services = db.query(Service).filter(Service.is_active == True).all()
            
            if not services:
                return "Actualmente no tenemos servicios disponibles."

            lines = []
            for s in services:
                name_low = s.name.lower()
                # Selección dinámica de iconos para verticalización
                icon = "✨"
                if "manicure" in name_low or "uñas" in name_low: icon = "💅"
                elif "pedicure" in name_low: icon = "👣"
                elif "ceja" in name_low or "pestaña" in name_low: icon = "👁️"
                elif "corte" in name_low or "pelo" in name_low: icon = "💇"
                
                lines.append(f"{icon} *{s.name}* ")
            
            return "\n".join(lines)
        except Exception as e:
            print(f"❌ [SERVICE-ORCH] Error al leer catálogo: {e}")
            return "No pude cargar el catálogo en este momento."

    def process_service_query(self, db: Session, state: dict) -> tuple[str, list]:
        """
        Método principal llamado por el Master cuando el usuario 
        pregunta específicamente por precios o servicios.
        """
        print(f"📡 [SERVICE-ORCH] Procesando consulta de catálogo para {state.get('phone')}")
        
        user_name = state.get("user_name", "cliente")
        catalog = self.get_catalog_summary(db)
        msgs = state.get("messages", [])

        # Construimos la respuesta enfocada en el catálogo
        res = (
            f"¡Claro que sí, {user_name}! Aquí tienes nuestra lista de servicios y precios:\n\n"
            f"{catalog}\n\n"
            "¿Te gustaría agendar una cita para alguno de ellos?"
        )

        # Actualizamos el historial de mensajes
        msgs.append({"role": "assistant", "content": res})
        
        return res, msgs