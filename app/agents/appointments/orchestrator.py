"""
AppointmentsOrchestrator — Dominio: Appointments
Responsabilidad: Gestionar la confirmación final de citas.
Si falta la hora, usa IA de rescate, registra el fallo para aprendizaje
y detecta si debe devolver el flujo al Master/Booking para cambiar de fecha.
"""

import os
from datetime import datetime
from sqlalchemy.orm import Session
from openai import OpenAI

from app.agents.appointments.graph_builder import create_appointments_graph
from app.models.services import Service
from app.models.learning import AiLearningLog

# Inicializamos el cliente de OpenAI
client_ai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class AppointmentsOrchestrator:

    def process(self, db: Session, state: dict):
        service_name = state.get("service_type")
        
        # 1. Capturar el mensaje real del usuario (el último mensaje del rol 'user')
        user_msg = next(
            (m["content"] for m in reversed(state["messages"]) if m["role"] == "user"), 
            "Mensaje no detectado"
        )

        # 2. Inyectar service_id y duración para el flujo técnico del grafo
        srv = db.query(Service).filter(Service.name == service_name).first()
        if srv:
            state["service_id"] = srv.id
            state["service_duration_minutes"] = srv.duration_minutes

        # 3. Ejecutar grafo técnico (extractor -> confirmation)
        graph = create_appointments_graph(db)
        final_state = graph.invoke(state)

        time_str = final_state.get("appointment_time")
        status   = final_state.get("confirmation_status")
        appt_id  = final_state.get("appointment_id")

        # Sincronizamos la hora detectada
        state["appointment_time"] = time_str

        # Formatear fecha para la respuesta de Valeria
        date_str = state.get("appointment_date", "")
        try:
            date_fmt = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            date_fmt = date_str

        # --- 🧠 LÓGICA DE RESCATE Y APRENDIZAJE ---
        if not time_str:
            # Valeria intenta responder de forma natural
            system_prompt = (
                f"Eres Valeria de 'Beauty Pro'. El cliente está agendando {service_name} el {date_fmt}.\n"
                "No se detectó una hora específica. Responde de forma breve (máx 20 palabras).\n"
                "Si el cliente menciona otro día o franja horaria, confirma que vas a revisar la disponibilidad."
            )

            response_ia = client_ai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_prompt}] + state["messages"],
                temperature=0.2 
            )
            res = response_ia.choices[0].message.content

            # --- 📊 LOG PARA APRENDIZAJE (Neon) ---
            try:
                new_log = AiLearningLog(
                    phone=state.get("phone", "unknown"),
                    module_name="appointments",
                    user_message=user_msg,
                    ai_response=res,
                    is_resolved=False,
                    notes=f"Fallo extracción hora. Estado fecha: {date_str}"
                )
                db.add(new_log)
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"❌ Error en log: {e}")

            # --- 🔄 REDIRECCIÓN ESTRATÉGICA ---
            # Si el usuario menciona un cambio de tiempo, reseteamos para que el Master lo mande a Booking
            msg_clean = user_msg.lower()
            trigger_words = ["mañana", "lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo", "día", "cambiar"]
            
            if any(word in msg_clean for word in trigger_words):
                print(f"🔄 [Orchestrator] Detectado posible cambio de fecha. Reseteando para volver a Booking.")
                state["appointment_date"] = None # Esto fuerza al Master a re-evaluar el día
                state["slots_shown"] = False

            # Lógica de salida por despedida
            if any(k in msg_clean for k in ["adios", "chao", "gracias", "olvidalo"]):
                state["appointment_date"] = None
                state["slots_shown"] = False

        # --- 4. LÓGICA DE ESTADOS DEL GRAFO ---
        elif status == "confirmed":
            res = (
                f"¡Todo listo! Tu cita de **{service_name}** quedó agendada para el "
                f"{date_fmt} a las {time_str} 🎉 (Ref: #{appt_id})"
            )
            state["appointment_date"]  = None
            state["appointment_time"]  = None
            state["slots_shown"]       = False
            state["booking_confirmed"] = True

        elif status == "conflict":
            reason = final_state.get("conflict_reason", "")
            res = f"Ese horario ya no está disponible ({reason}). ¿Quieres elegir otro?"
            state["slots_shown"] = True

        elif status == "no_collaborator":
            res = "No tenemos profesionales libres a esa hora. ¿Probamos con otro horario?"
            state["slots_shown"] = True

        elif status == "missing_data":
            res = f"Me falta información. ¿Para qué día querías la cita de **{service_name}**?"
            state["slots_shown"] = False

        else:
            res = "Hubo un problema al procesar la cita. ¿Qué horario prefieres?"
            state["slots_shown"] = True

        # Guardar respuesta final en el historial
        state["messages"].append({"role": "assistant", "content": res})
        return res, state["messages"]