# app/agents/booking/orchestrator.py

from datetime import datetime
from sqlalchemy.orm import Session
from app.agents.booking.graph_builder import create_booking_graph
from app.models.services import Service
from app.services.appointment_service import AppointmentService  # <--- Importamos tu nuevo servicio

class BookingOrchestrator:

    def process_booking(self, db: Session, state: dict):
        """
        Gestiona el flujo de reserva (booking), validando disponibilidad 
        real por departamento y colaborador.
        """
        service_name = state.get("service_type")
        srv = db.query(Service).filter(Service.name == service_name).first()

        if not srv:
            return "Perdí el hilo del servicio. ¿Qué querías hacerte?", state["messages"]

        # Preparamos el estado para el grafo
        state["service_id"]   = srv.id
        state["current_date"] = datetime.now().strftime("%Y-%m-%d")

        # 1. EJECUTAMOS EL GRAFO (Extractor de fechas/horas y cálculo inicial de slots)
        graph       = create_booking_graph(db)
        final_state = graph.invoke(state)

        # Recuperamos lo que la IA extrajo o lo que ya teníamos guardado
        date     = final_state.get("appointment_date") or state.get("appointment_date")
        time_sel = final_state.get("appointment_time")
        slots    = final_state.get("available_slots")

        # Sincronizamos el estado
        state["appointment_date"] = date
        state["appointment_time"] = time_sel

        # --- 🚀 VALIDACIÓN DE COLABORADOR DISPONIBLE (Lógica Nueva) ---
        # Si el usuario ya proporcionó una fecha y una hora específica, verificamos si es real
        if date and time_sel:
            try:
                # Convertimos la cadena de texto a objeto datetime para el servicio
                dt_string = f"{date} {time_sel}"
                dt_obj = datetime.strptime(dt_string, "%Y-%m-%d %H:%M")
                
                # Consultamos: ¿Hay alguien de ese departamento libre a esa hora?
                available_colabs = AppointmentService.get_available_collaborators(db, srv.id, dt_obj)
                
                # REGLA DE ORO: Si no hay nadie disponible, invalidamos la hora
                if not available_colabs:
                    print(f"⚠️ [Booking] Bloqueo: {service_name} a las {time_sel} no tiene personal libre.")
                    state["appointment_time"] = None  # Borramos la hora del estado
                    
                    res = (f"Lo siento, para el servicio de **{service_name}** a las {time_sel} "
                           f"ya no tenemos especialistas disponibles. 😕\n\n"
                           f"¿Te gustaría intentar en otro horario?")
                    
                    state["messages"].append({"role": "assistant", "content": res})
                    return res, state["messages"]
                
                print(f"✅ [Booking] {len(available_colabs)} colaborador(es) apto(s) para {service_name}")
                
            except ValueError:
                # En caso de que el formato de hora no sea el esperado, ignoramos la validación
                print("❌ [Booking] Error de formato en fecha/hora durante validación.")

        # --- 🚦 CONSTRUCCIÓN DE LA RESPUESTA ---
        
        # Caso A: No tenemos fecha todavía
        if not date:
            state["slots_shown"] = False
            res = f"¡Perfecto! Para agendar tu cita de **{service_name}**, dime: ¿qué día te vendría bien?"

        # Caso B: Hay fecha, pero no hay huecos (slots) en general
        elif slots in ("Sin disponibilidad", None, ""):
            state["slots_shown"] = False
            date_fmt = datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")
            res = f"Para el {date_fmt} no me quedan huecos libres para **{service_name}**. ¿Quieres intentar otro día?"

        # Caso C: Todo OK, mostramos los horarios disponibles
        else:
            state["slots_shown"] = True
            date_fmt = datetime.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y")
            res = f"Para **{service_name}** el {date_fmt} tengo estos huecos libres: {slots}. ¿Cuál prefieres?"

        state["messages"].append({"role": "assistant", "content": res})
        return res, state["messages"]