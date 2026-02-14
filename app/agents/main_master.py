import os
import re
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.agents.identity.orchestrator import IdentityOrchestrator
from app.agents.service.orchestrator import ServiceOrchestrator
from app.agents.booking.orchestrator import BookingOrchestrator
from app.agents.appointments.orchestrator import AppointmentsOrchestrator
from app.agents.config import SERVICE_KEYWORDS, BOOKING_KEYWORDS, CONFIRMATION_KEYWORDS
from app.models.clients import Client
from app.models.services import Service
from app.agents.booking.nodes.extractor_node import extractor_node # Importante para el pre-check

class ValeriaMaster:
    def __init__(self):
        self.identity     = IdentityOrchestrator()
        self.service      = ServiceOrchestrator()
        self.booking      = BookingOrchestrator()
        self.appointments = AppointmentsOrchestrator()

    def process(self, db: Session, phone: str, message: str, history: list):
        # 1. Contexto básico y normalización
        state = self.identity.get_user_context(db, phone, message, history)
        msg_raw = message.lower().strip()
        msg_clean = msg_raw.translate(str.maketrans("áéíóú", "aeiou"))
        
        # --- 🕒 DETECCIÓN TEMPRANA (IA EXTRACTOR) ---
        # Ejecutamos el extractor ANTES del routing para saber qué quiere el usuario realmente
        state["current_date"] = datetime.now().strftime("%Y-%m-%d")
        extracted = extractor_node(state)
        
        # Si la IA detectó algo nuevo, lo priorizamos en el state
        if extracted.get("appointment_date"):
            state["appointment_date"] = extracted["appointment_date"]
        if extracted.get("appointment_time"):
            state["appointment_time"] = extracted["appointment_time"]

        # --- 🛡️ CARGA DE DATOS DEL CLIENTE ---
        client = db.query(Client).filter(Client.phone == phone).first()
        db_service_name = None
        if client and client.current_service_id:
            srv = db.query(Service).filter(Service.id == client.current_service_id).first()
            if srv:
                db_service_name = srv.name

        if db_service_name:
            state["service_type"] = db_service_name
            has_service = True
        else:
            has_service = False

        # Recuperar persistencia de metadata
        if client and client.metadata_json:
            if not state.get("appointment_date"):
                state["appointment_date"] = client.metadata_json.get("appointment_date")
            if not state.get("appointment_time"):
                state["appointment_time"] = client.metadata_json.get("appointment_time")
            state["slots_shown"] = client.metadata_json.get("slots_shown", False)

        # 2. Detección de intenciones
        is_service_intent      = any(k in msg_clean for k in SERVICE_KEYWORDS)
        is_booking_intent      = any(k in msg_clean for k in BOOKING_KEYWORDS)
        is_confirmation_intent = any(k in msg_clean for k in CONFIRMATION_KEYWORDS)
        has_time_ref           = any(k in msg_clean for k in [":", " am", " pm", " a las "]) or re.search(r'\d+', msg_clean)

        # Buscar si mencionó un servicio específico
        all_services = db.query(Service).filter(Service.is_active == True).all()
        service_mentioned = next((s for s in sorted(all_services, key=lambda x: len(x.name), reverse=True) 
                                 if s.name.lower().translate(str.maketrans("áéíóú", "aeiou")) in msg_clean), None)

        # --- 🚦 ROUTING (Prioridad de Cierre) ---

        # REGLA 1: Cambio de servicio
        if service_mentioned:
            print(f"🔄 [Master] Selección de servicio: {service_mentioned.name}")
            if has_service and db_service_name != service_mentioned.name:
                self._clear_booking_state(db, client)
                state["appointment_date"] = state["appointment_time"] = None
            state["service_type"] = service_mentioned.name
            response, updated_history = self.service.process_service(db, state)

        # REGLA 2: ¡EL SALTO CRÍTICO! Si ya tenemos FECHA y HORA -> Ir a confirmar
        elif has_service and state.get("appointment_date") and state.get("appointment_time"):
            print(f"🚀 [Master] Cierre detectado (Fecha: {state['appointment_date']}, Hora: {state['appointment_time']})")
            response, updated_history = self.appointments.process(db, state)
            if state.get("booking_confirmed"):
                self._clear_booking_state(db, client)

        # REGLA 3: Intento de confirmación (tiene fecha, pero falta hora exacta)
        elif has_service and state.get("appointment_date") and (has_time_ref or state.get("slots_shown")):
            print(f"📌 [Master] Flujo: Refinamiento de Cita")
            response, updated_history = self.appointments.process(db, state)

        # REGLA 4: Confirmación simple sin hora (vale, ok) -> Mostrar disponibilidad
        elif has_service and is_confirmation_intent and state.get("appointment_date"):
            print(f"📅 [Master] Flujo: Mostrar disponibilidad (Booking)")
            response, updated_history = self.booking.process_booking(db, state)

        # REGLA 5: Booking o Catálogo inicial
        elif is_service_intent or is_booking_intent:
            if has_service:
                print(f"📅 [Master] Flujo: Booking")
                response, updated_history = self.booking.process_booking(db, state)
            else:
                print(f"🔍 [Master] Flujo: Catálogo")
                response, updated_history = self.service.process_service(db, state)

        # REGLA 6: Charla casual
        else:
            print(f"💬 [Master] Flujo: Charla Casual")
            response = state["messages"][-1]["content"]
            updated_history = state["messages"]

        self._sync_memory(db, phone, state, client)
        return response, updated_history

    def _sync_memory(self, db: Session, phone: str, state: dict, client: Client = None):
        if not client: return
        service_name = state.get("service_type")
        if service_name and service_name != "not_found":
            srv = db.query(Service).filter(Service.name == service_name).first()
            if srv: client.current_service_id = srv.id

        if client.metadata_json is None: client.metadata_json = {}
        client.metadata_json.update({
            "last_interaction": state["messages"][-1]["content"][:100],
            "appointment_date": state.get("appointment_date"),
            "appointment_time": state.get("appointment_time"),
            "slots_shown": state.get("slots_shown", False)
        })
        flag_modified(client, "metadata_json")
        try:
            db.commit()
            print(f"💾 [DB] Memoria sincronizada para {phone}")
        except Exception as e:
            db.rollback()
            print(f"❌ [DB] Error: {e}")

    def _clear_booking_state(self, db: Session, client: Client):
        if not client or not client.metadata_json: return
        for key in ["appointment_date", "appointment_time", "slots_shown"]:
            client.metadata_json.pop(key, None)
        flag_modified(client, "metadata_json")
        db.commit()
        print(f"🧹 [DB] Estado de booking reseteado.")