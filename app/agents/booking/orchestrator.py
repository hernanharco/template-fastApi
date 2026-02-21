from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Tuple, Dict
import re
from app.agents.booking.fuzzy_logic import service_fuzzy_match
from app.agents.booking.nodes.availability_node import availability_node

class BookingOrchestrator:
    """
    SRP: Orquestar el flujo de reserva, normalizar datos y gestionar el estado temporal.
    """

    def _extract_relative_date(self, message: str) -> datetime:
        """
        SRP: ÚNICAMENTE extrae la fecha. No valida si es pasado o futuro.
        """
        today = datetime.now()
        msg_lower = message.lower()

        if "mañana" in msg_lower and "pasado" not in msg_lower:
            return today + timedelta(days=1)
        if "pasado mañana" in msg_lower:
            return today + timedelta(days=2)

        dias_semana = {
            "lunes": 0, "martes": 1, "miércoles": 2, "miercoles": 2,
            "jueves": 3, "viernes": 4, "sábado": 5, "sabado": 5, "domingo": 6,
        }

        for dia, target_weekday in dias_semana.items():
            if dia in msg_lower:
                current_weekday = today.weekday()
                days_ahead = (target_weekday - current_weekday) % 7
                if days_ahead == 0: days_ahead = 7
                return today + timedelta(days=days_ahead)
        return None

    def process_booking(self, db: Session, state: dict, raw_message: str) -> Tuple[str, List]:
        print(f"\n--- 🧬 [ORCH-BOOKING] Iniciando Orquestación ---")
        
        # 1. CAPTURA DE HORA
        time_match = re.search(r"(\d{1,2})[:.](\d{2})", raw_message)
        if time_match:
            hour, minute = time_match.groups()
            state["appointment_time"] = f"{hour.zfill(2)}:{minute}"

        # 2. CAPTURA DE FECHA
        relative_date = self._extract_relative_date(raw_message)
        if relative_date:
            state["appointment_date"] = relative_date.strftime("%Y-%m-%d")
        
        # 🛡️ ASEGURAR FECHA ACTUAL (Default si no hay una)
        if not state.get("appointment_date"):
            state["appointment_date"] = datetime.now().strftime("%Y-%m-%d")

        # --- [NUEVO] 3. VALIDACIÓN PREVENTIVA DE PASADO ---
        # Si ya tenemos fecha y hora, verificamos antes de seguir
        if state.get("appointment_date") and state.get("appointment_time"):
            try:
                dt_str = f"{state['appointment_date']} {state['appointment_time']}"
                appointment_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
                
                if appointment_dt < datetime.now():
                    print(f"⚠️ [ORCH-BOOKING] Bloqueo preventivo: Fecha pasada detectada.")
                    res = (
                        f"¡Ups! Me pides una cita para las {state['appointment_time']}, "
                        "pero esa hora ya pasó. ¿Podrías decirme otra hora o para otro día?"
                    )
                    state["appointment_time"] = None # Limpiamos la hora para corregir
                    return res, self._update_history(state, res)
            except Exception as e:
                print(f"Error validando tiempo: {e}")

        # 4. NORMALIZACIÓN DEL SERVICIO (Fuzzy matching)
        if not state.get("service_id"):
            match = service_fuzzy_match(db, raw_message)
            if match:
                state["service_type"], state["service_id"] = match

        # 5. LÓGICA DE DECISIÓN
        has_time = state.get("appointment_time") is not None
        has_service = state.get("service_id") is not None
        
        if has_time and has_service:
            print(f"🚀 [ORCH-BOOKING] Todo listo. Pasando a confirmación.")
            return self._handle_confirmation(db, state)

        # Fallback: Consultar disponibilidad
        print("🔍 [ORCH-BOOKING] Información incompleta. Consultando disponibilidad...")
        response_text = availability_node(db, state)
        return response_text, self._update_history(state, response_text)

    def _handle_confirmation(self, db: Session, state: dict) -> Tuple[str, List]:
        from app.agents.appointments.orchestrator import AppointmentsOrchestrator
        return AppointmentsOrchestrator().process(db, state)

    def _update_history(self, state: dict, response: str) -> list:
        if "messages" not in state: state["messages"] = []
        state["messages"].append({"role": "assistant", "content": response})
        return state["messages"]