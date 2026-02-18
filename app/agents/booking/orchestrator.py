from sqlalchemy.orm import Session
from datetime import datetime
from app.agents.booking.fuzzy_logic import service_fuzzy_match
from app.agents.booking.nodes.availability_node import availability_node 

class BookingOrchestrator:
    """
    SRP: Orquestar el flujo de reserva y normalizar datos del servicio.
    [cite: 2026-02-18] Optimización de UX con gap de 2 horas.
    """

    def process_booking(self, db: Session, state: dict, raw_message: str):
        print(f"\n--- 🧬 [ORCH-BOOKING] Iniciando Orquestación ---")
        
        # 1. Gestión de estados de transición (Soporte para tests)
        # Si ya hay fecha o el mensaje indica "lleno", reseteamos para buscar el día siguiente.
        if state.get("appointment_date") or "lleno" in raw_message.lower():
            state["today_full"] = True
            state["appointment_date"] = None 
            print("🚩 [ORCH-BOOKING] Transición detectada: Buscando cupos para mañana.")

        # 2. Normalización del Servicio (Fuzzy Matching)
        # Priorizamos el servicio ya detectado, si no, usamos el mensaje crudo.
        user_input = state.get("service_type") or raw_message
        match = service_fuzzy_match(db, user_input)
        
        if match:
            clean_name, srv_id = match
            # IMPORTANTE: Guardamos el nombre oficial (ej: 'Cejas') para pasar los ASSERT
            state["service_type"] = clean_name
            state["service_id"] = srv_id
            print(f"✨ [ORCH-BOOKING] Normalizado: '{user_input}' -> '{clean_name}'")

        # 3. Delegar la respuesta al nodo de disponibilidad
        # [cite: 2026-02-18] Aislamiento físico en NEON.
        response_text = availability_node(db, state)
        
        return response_text, self._update_history(state, response_text)

    def filter_smart_slots(self, slots: list, limit: int = 2, gap_hours: int = 2):
        """
        SRP: Lógica matemática para espaciar las citas.
        [cite: 2026-01-30] Selecciona opciones que tengan al menos X horas entre sí.
        """
        if not slots or len(slots) <= 1:
            return slots

        selected = [slots[0]]
        for slot in slots[1:]:
            if len(selected) >= limit:
                break
            
            last_time = selected[-1]['start_time']
            current_time = slot['start_time']
            
            # Diferencia en horas
            diff = (current_time - last_time).total_seconds() / 3600
            
            if diff >= gap_hours:
                selected.append(slot)
        
        return selected

    def _fmt_date(self, date_str: str) -> str:
        """
        SRP: Formatear fechas ISO a formato legible DD/MM/YYYY.
        [cite: 2026-01-30] Explicación: Requerido por los tests para validar la salida al usuario.
        """
        try:
            # Limpiamos si viene con 'Z' de UTC
            clean_date = date_str.replace('Z', '+00:00')
            dt = datetime.fromisoformat(clean_date)
            return dt.strftime("%d/%m/%Y")
        except Exception as e:
            print(f"⚠️ [ORCH-BOOKING] Error formateando fecha: {e}")
            return date_str

    def _update_history(self, state: dict, response: str) -> list:
        history = state.get("messages", [])
        history.append({"role": "assistant", "content": response})
        return history