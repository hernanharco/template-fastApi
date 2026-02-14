from sqlalchemy.orm import Session
from app.models.services import Service


class ServiceOrchestrator:
    def process_service(self, db: Session, state: dict):
        # ✅ Buscar el último mensaje del USUARIO, no el último en general
        # (el último puede ser del asistente tras pasar por greeting_node)
        messages   = state.get("messages", [])
        user_msgs  = [m for m in messages if m.get("role") == "user"]
        message    = user_msgs[-1]["content"].lower().strip() if user_msgs else ""

        current_service = state.get("service_type")

        services = db.query(Service).filter(Service.is_active == True).all()
        selected_srv = None

        for s in services:
            nombre_db = s.name.lower()
            # Normalizar tildes del mensaje para comparar
            msg_clean = (message
                .replace("á","a").replace("é","e").replace("í","i")
                .replace("ó","o").replace("ú","u"))
            nom_clean = (nombre_db
                .replace("á","a").replace("é","e").replace("í","i")
                .replace("ó","o").replace("ú","u"))
            if nom_clean in msg_clean or ("acril" in msg_clean and "acril" in nom_clean):
                selected_srv = s
                break

        # CASO A: El usuario acaba de elegir un servicio AHORA
        if selected_srv:
            state["service_type"] = selected_srv.name
            print(f"✅ [Service] Match nuevo: {selected_srv.name}")

            if state.get("appointment_date"):
                response = (
                    f"¡Perfecto! **{selected_srv.name}** anotado. "
                    f"Ya me dijiste que querías el {state['appointment_date']}, "
                    f"déjame ver los huecos disponibles..."
                )
            else:
                response = f"¡Perfecto! He anotado **{selected_srv.name}**. ¿Para qué día y hora te gustaría agendar?"

            state["messages"].append({"role": "assistant", "content": response})
            return response, state["messages"]

        # CASO B: Ya teníamos servicio guardado
        elif current_service and current_service != "not_found":
            response = f"Seguimos con tu cita para **{current_service}**. ¿Qué día te viene bien?"
            return response, state["messages"]

        # CASO C: Mostrar menú
        menu = "¡Claro! ¿Qué te gustaría hacerte? Aquí tienes nuestras opciones:\n"
        for s in services:
            menu += f"• {s.name} (${s.price})\n"

        state["messages"].append({"role": "assistant", "content": menu})
        return menu, state["messages"]