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
        state["current_date"] = datetime.now().strftime("%Y-%m-%d")
        extracted = extractor_node(state)

        state["phone"] = phone
        
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
        
        # 🚩 NUEVA DETECCIÓN: ¿El usuario quiere cambiar o ver el catálogo?
        change_keywords = ["otra cosa", "otro servicio", "cambiar", "menu", "catalogo", "servicios"]
        wants_to_change = any(k in msg_clean for k in change_keywords)
        
        has_time_ref = any(k in msg_clean for k in [":", " am", " pm", " a las "]) or re.search(r'\d+', msg_clean)

        # Buscar si mencionó un servicio específico
        all_services = db.query(Service).filter(Service.is_active == True).all()
        service_mentioned = next((s for s in sorted(all_services, key=lambda x: len(x.name), reverse=True) 
                                 if s.name.lower().translate(str.maketrans("áéíóú", "aeiou")) in msg_clean), None)

        # --- 🚦 ROUTING (Lógica Pulida) ---

        # Si el cliente es nuevo o genérico, y el mensaje actual no parece contener su nombre

        if state.get("is_new_client") and state.get("client_name") == "Usuario":
            # Si el mensaje es corto y no tiene intención de cita, preguntamos nombre
            # Pero si el mensaje es largo (ej: "Soy Hernan y quiero cita"), el orquestador 
            # de identidad ya debería haber actualizado el client_name en el state.
            if len(msg_clean.split()) < 2: 
                response = "¡Hola! Bienvenid@ a nuestro centro. 😊 Veo que es tu primera vez por aquí. ¿Me podrías decir tu nombre para atenderte mejor?"
                # Guardamos antes de salir para no perder el hilo
                self._sync_memory(db, phone, state, client)
                return response, state["messages"] + [{"role": "assistant", "content": response}]
    
    # Si llegamos aquí y sigue siendo "Usuario", es que el mensaje era largo pero 
    # no contenía un nombre claro. Podríamos dejarlo pasar o insistir.

        # REGLA 0: ¡CAMBIO DE OPINIÓN EXPLÍCITO! 
        # Si el usuario dice "quiero otra cosa", limpiamos el estado y mandamos al catálogo.
        if wants_to_change and not service_mentioned:
            print(f"🧹 [Master] Usuario quiere cambiar de opinión. Limpiando estado...")
            self._clear_booking_state(db, client)
            state["service_type"] = None
            response, updated_history = self.service.process_service(db, state)

        # REGLA 1: Selección de un servicio específico por nombre
        elif service_mentioned:
            print(f"🔄 [Master] Match de servicio: {service_mentioned.name}")
            if has_service and db_service_name != service_mentioned.name:
                self._clear_booking_state(db, client)
                state["appointment_date"] = state["appointment_time"] = None
            state["service_type"] = service_mentioned.name
            response, updated_history = self.service.process_service(db, state)

        # REGLA 2: Confirmación final (Fecha + Hora presentes)
        elif has_service and state.get("appointment_date") and state.get("appointment_time"):
            print(f"🚀 [Master] Cierre detectado")

            state["phone"] = phone

            response, updated_history = self.appointments.process(db, state)
            if state.get("booking_confirmed"):
                self._clear_booking_state(db, client)

        # REGLA 3: Refinamiento (Tiene fecha, busca hora)
        elif has_service and state.get("appointment_date") and (has_time_ref or state.get("slots_shown")):
            print(f"📌 [Master] Refinamiento")
            response, updated_history = self.appointments.process(db, state)

        # REGLA 4: Flujo de disponibilidad (Booking)
        elif is_service_intent or is_booking_intent or (has_service and is_confirmation_intent):
            if has_service:
                print(f"📅 [Master] Flujo: Booking")
                response, updated_history = self.booking.process_booking(db, state)
            else:
                print(f"🔍 [Master] Flujo: Catálogo")
                response, updated_history = self.service.process_service(db, state)

        # REGLA 5: Charla casual
        else:
            print(f"💬 [Master] Flujo: Charla Casual")
            response = state["messages"][-1]["content"]
            updated_history = state["messages"]

        self._sync_memory(db, phone, state, client)
        return response, updated_history

    def _sync_memory(self, db: Session, phone: str, state: dict, client: Client = None):
        if not client: return

        # 1. Gestión del Servicio Actual (current_service_id)
        # Si la cita ya se confirmó, limpiamos el servicio para que la próxima charla empiece de cero
        if state.get("booking_confirmed"):
            client.current_service_id = None
            state["service_type"] = None
            print(f"✅ [Memory] Cita confirmada. Limpiando servicio actual para {phone}")
        else:
            service_name = state.get("service_type")
            if service_name and service_name != "not_found":
                srv = db.query(Service).filter(Service.name == service_name).first()
                if srv: 
                    client.current_service_id = srv.id
            else:
                # Si no hay un servicio claro en el estado, lo limpiamos en la DB
                client.current_service_id = None

        # 2. Gestión de Metadata (JSONB en Neon)
        if client.metadata_json is None: 
            client.metadata_json = {}

        # Actualizamos la persistencia con lo que pasó en esta interacción
        client.metadata_json.update({
            "last_interaction": state["messages"][-1]["content"][:100],
            "appointment_date": state.get("appointment_date"),
            "appointment_time": state.get("appointment_time"),
            "slots_shown": state.get("slots_shown", False)
        })

        # Si confirmamos cita, también limpiamos los datos temporales del JSON
        if state.get("booking_confirmed"):
            client.metadata_json.pop("appointment_date", None)
            client.metadata_json.pop("appointment_time", None)
            client.metadata_json.pop("slots_shown", None)

        # 3. Guardado físico en DB
        # Notificamos a SQLAlchemy que el JSON cambió
        flag_modified(client, "metadata_json")
        
        try:
            db.commit()
            print(f"💾 [DB] Memoria sincronizada correctamente para {phone}")
        except Exception as e:
            db.rollback()
            print(f"❌ [DB] Error al sincronizar memoria: {e}")

    def _clear_booking_state(self, db: Session, client: Client):
        if not client or not client.metadata_json: return
        for key in ["appointment_date", "appointment_time", "slots_shown"]:
            client.metadata_json.pop(key, None)
        flag_modified(client, "metadata_json")
        db.commit()
        print(f"🧹 [DB] Estado de booking reseteado.")