import os
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.appointments import Appointment, AppointmentSource 
from app.models.services import Service
from app.models.collaborators import Collaborator

class AppointmentsOrchestrator:
    """
    SRP: Orquestar la ejecución del grafo de agendamiento.
    [cite: 2026-02-19] Fix: Importación local para evitar Circular Import.
    """

    def process(self, db: Session, state: dict):
        print(f"\n--- 🧬 [ORCH-APPOINTMENTS] Iniciando Proceso de Persistencia ---")
        
        # 1. RECUPERACIÓN DE IDENTIDAD (Identificamos al usuario) 🛡️
        phone = state.get("phone") or state.get("user_id") or state.get("sender_id")
        if not phone:
            print("❌ [Orchestrator] Error: No se encontró teléfono en el estado.")
            return "Hubo un problema con tu identificación. ¿Podrías saludar de nuevo?", state.get("messages", [])
        
        state["phone"] = phone
        service_name = state.get("service_type")
        
        # 2. VALIDACIÓN DEL SERVICIO
        srv = db.query(Service).filter(Service.id == state.get("service_id")).first()
        if not srv:
            srv = db.query(Service).filter(Service.name == service_name).first()
        
        if not srv:
            return "Lo siento, no identifiqué el servicio. ¿Qué te gustaría agendar?", state.get("messages", [])

        state["service_id"] = srv.id
        state["service_duration_minutes"] = srv.duration_minutes
        
        # 3. NORMALIZACIÓN DE FECHA
        now = datetime.now()
        current_date = state.get("appointment_date") or now.strftime("%Y-%m-%d")
        state["appointment_date"] = current_date

        # 4. AUTO-ASIGNACIÓN DE COLABORADOR (Fix para evitar datos insuficientes) 🕵️
        if not state.get("collaborator_id"):
            print(f"🕵️ [Orchestrator] Buscando colaborador disponible para: {srv.name}")
            colab = db.query(Collaborator).filter(
                Collaborator.is_active == True,
                Collaborator.departments.any(id=srv.department_id)
            ).first()

            if colab:
                state["collaborator_id"] = colab.id
                print(f"✅ [Orchestrator] Auto-asignado: {colab.name} (ID: {colab.id})")
            else:
                return self._handle_failure(db, state, srv)

        # 5. CONFIGURACIÓN DE ORIGEN (String compatible con tu nuevo modelo)
        state["source"] = "ia"

        # 6. EJECUCIÓN DEL GRAFO (Resolución del Circular Import) 🚀
        try:
            # Importamos aquí dentro para romper el ciclo de dependencia
            from app.agents.appointments.graph_builder import create_appointments_graph
            
            graph = create_appointments_graph(db)
            print(f"🧬 [GRAPH] Invocando grafo para agendar a las {state.get('appointment_time')}...")
            
            final_state = graph.invoke(state)
            appointment_id = final_state.get("appointment_id")
            
            if appointment_id:
                time_str = state.get("appointment_time")
                date_fmt = self._format_date(current_date)
                res = f"¡Excelente noticia! 🎉 Tu cita para *{srv.name}* ha sido agendada con éxito para el {date_fmt} a las {time_str}. ¡Te esperamos! ✨"
                state["booking_confirmed"] = True
                return self._finalize_response(state, res)

        except Exception as e:
            print(f"🔥 [Orchestrator] ERROR CRÍTICO: {str(e)}")
            import traceback
            traceback.print_exc() # Para ver el error completo en consola
            db.rollback()

        return self._handle_failure(db, state, srv)

    def _handle_failure(self, db: Session, state: dict, srv: Service):
        print(f"⚠️ [Orchestrator] Fallo en confirmación. Buscando alternativas...")
        time_str = state.get("appointment_time", "esa hora")
        
        # Reseteamos para que BookingOrchestrator busque disponibilidad real
        state["appointment_time"] = None 
        state["booking_confirmed"] = False
        
        from app.agents.booking.orchestrator import BookingOrchestrator
        booking_engine = BookingOrchestrator()
        res_booking, _ = booking_engine.process_booking(db, state, "disponibilidad")
        
        res = (
            f"Me temo que para las {time_str} no tengo disponibilidad. 😅\n\n"
            f"Pero tengo estos otros huecos libres:\n\n{res_booking}\n\n"
            "¿Te sirve alguno o prefieres otro día?"
        )
        return self._finalize_response(state, res)

    def _format_date(self, date_str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
        except: return date_str

    def _finalize_response(self, state, response_text):
        if "messages" not in state: state["messages"] = []
        state["messages"].append({"role": "assistant", "content": response_text})
        return response_text, state["messages"]