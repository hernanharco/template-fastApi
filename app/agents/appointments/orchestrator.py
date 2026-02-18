import os
from datetime import datetime
from sqlalchemy.orm import Session
from app.agents.appointments.graph_builder import create_appointments_graph
from app.models.appointments import Appointment, AppointmentSource 
from app.models.services import Service

class AppointmentsOrchestrator:

    def process(self, db: Session, state: dict):
        service_name = state.get("service_type")
        phone = state.get("phone")
        
        # 1. PREPARACIÓN Y VALIDACIÓN DEL SERVICIO
        srv = db.query(Service).filter(Service.id == state.get("service_id")).first()
        if not srv:
            srv = db.query(Service).filter(Service.name == service_name).first()
        
        if not srv:
            return "Lo siento, no pude identificar el servicio. ¿Empezamos de nuevo?", state["messages"]

        # Enriquecemos el estado con datos técnicos
        state["service_id"] = srv.id
        state["service_duration_minutes"] = srv.duration_minutes
        
        # 🛡️ LIMPIEZA DE FECHA (Evita el bucle del 17/02 si hoy es 18/02)
        today_str = datetime.now().strftime("%Y-%m-%d")
        current_date = state.get("appointment_date")
        
        if current_date and current_date < today_str:
            print(f"♻️ [Orchestrator] Fecha pasada detectada ({current_date}). Reseteando a hoy.")
            state["appointment_date"] = today_str

        # 🤖 INYECCIÓN DEL ORIGEN (Tu requerimiento principal)
        # Inyectamos el valor string para que Neon lo guarde sin errores de Enum
        state["source"] = AppointmentSource.IA.value 

        # 2. EJECUCIÓN DEL GRAFO DE AGENDAMIENTO
        status = None
        try:
            db.commit() 
            graph = create_appointments_graph(db)
            final_state = graph.invoke(state)
            
            status = final_state.get("confirmation_status")
            apt_id = final_state.get("appointment_id")
            
            # Actualizamos el estado con lo que devolvió el grafo
            if apt_id or status == "confirmed":
                status = "confirmed"
            
        except Exception as e:
            print(f"🔥 [Appointments] Error en Grafo: {e}")
            db.rollback()

        # 3. VERIFICACIÓN DE RESPALDO (Falso Negativo Recovery)
        if status != "confirmed":
            print(f"🕵️ [Appointments] Verificando DB para el teléfono {phone}...")
            last_apt = db.query(Appointment).filter(
                Appointment.client_phone == phone
            ).order_by(Appointment.id.desc()).first()

            if last_apt and last_apt.service_id == srv.id:
                if last_apt.created_at.date() == datetime.now().date():
                    print(f"✅ [Appointments] Cita #{last_apt.id} encontrada en Neon.")
                    status = "confirmed"

        # 4. GENERACIÓN DE RESPUESTA AL USUARIO
        time_str = state.get("appointment_time")
        date_raw = state.get("appointment_date", today_str)
        date_fmt = self._format_date(date_raw)

        if status == "confirmed":
            res = f"¡Excelente noticia! 🎉 Tu cita para *{srv.name}* ha sido agendada con éxito para el {date_fmt} a las {time_str}. ¡Te esperamos!"
            state["booking_confirmed"] = True
        else:
            # Caso de Fallo (Búsqueda de alternativas)
            print(f"⚠️ [Appointments] Sin cupo para {time_str} en {date_raw}. Buscando huecos...")
            state["appointment_time"] = None 
            state["booking_confirmed"] = False
            
            from app.agents.booking.orchestrator import BookingOrchestrator
            booking_engine = BookingOrchestrator()
            res_booking, _ = booking_engine.process_booking(db, state)
            
            res = (
                f"Me temo que para el {date_fmt} a esa hora no tengo disponibilidad. 😅\n\n"
                f"Pero aquí tienes otros horarios disponibles:\n"
                f"✨ {res_booking}\n\n"
                "¿Te sirve alguno o prefieres otro día?"
            )

        return self._finalize_response(state, res)

    def _format_date(self, date_str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
        except: 
            return date_str

    def _finalize_response(self, state, response_text):
        if "messages" not in state:
            state["messages"] = []
        state["messages"].append({"role": "assistant", "content": response_text})
        return response_text, state["messages"]