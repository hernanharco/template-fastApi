import os
from sqlalchemy.orm import Session
from app.models.services import Service

class ServiceOrchestrator:
    """
    SRP: Gestionar la información y visualización del catálogo de servicios.
    [cite: 2026-02-18] Persistencia unificada en NEON con trazabilidad.
    """

    def get_catalog_summary(self, db: Session) -> str:
        """
        Genera una lista amigable para el saludo proactivo del Master.
        [cite: 2026-02-18] Menos infraestructura, más valor.
        """
        print("📡 [SERVICE-ORCH] Generando resumen rápido del catálogo...")
        try:
            services = db.query(Service).filter(Service.is_active == True).all()
            if not services:
                print("⚠️ [SERVICE-ORCH] Sin servicios para el resumen.")
                return "Actualmente estamos actualizando nuestros servicios. 🌸"

            # Emojis para que la interacción no sea 'al aire'
            icons = {
                "cejas": "👁️", "pestañas": "✨", "manicura": "💅", 
                "pedicura": "👣", "facial": "🧖‍♀️", "masaje": "💆‍♂️"
            }

            lines = []
            for s in services:
                emoji = next((v for k, v in icons.items() if k in s.name.lower()), "🌸")
                # Incluimos el precio para que el usuario elija con info completa
                precio = f" - *${s.price}*" if hasattr(s, 'price') and s.price else ""
                lines.append(f"{emoji} **{s.name}**{precio}")
            
            return "\n".join(lines)
        except Exception as e:
            print(f"❌ [SERVICE-ORCH] Error en resumen: {str(e)}")
            return "Nuestros servicios de estética profesional."

    def process_service(self, db: Session, state: dict):
        """
        Lógica completa cuando el usuario pide explícitamente ver el catálogo.
        """
        print("\n" + "="*50)
        print("🔍 [SERVICE-ORCH] Iniciando flujo de ayuda detallada...")
        
        requested = state.get("service_type")
        print(f"📥 [SERVICE-ORCH] Input: '{requested}'")

        # Reutilizamos la lógica del summary para mantener consistencia
        servicios_list = self.get_catalog_summary(db)

        # Lógica de Mensajería Proactiva
        if requested and requested != "not_found":
            print(f"💡 [SERVICE-ORCH] Corrección de: '{requested}'")
            intro = f"No logré encontrar '{requested}' en nuestro sistema, pero mira lo que tenemos para ti: 😉"
        else:
            print("👋 [SERVICE-ORCH] Saludo inicial de catálogo.")
            intro = "¡Qué gusto saludarte! 👋 Aquí tienes nuestros servicios disponibles:"

        response = (
            f"{intro}\n\n"
            f"{servicios_list}\n\n"
            "¿Cuál de estos te gustaría elegir hoy?"
        )

        # Actualización de historia
        history = state.get("messages", [])
        history.append({"role": "assistant", "content": response})
        
        print("📤 [SERVICE-ORCH] Respuesta generada con éxito.")
        print("="*50 + "\n")
        
        return response, history