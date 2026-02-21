import os
from datetime import datetime
from typing import List, Tuple, Dict
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Orquestadores de Dominio
from app.agents.identity.orchestrator import IdentityOrchestrator
from app.agents.service.orchestrator import ServiceOrchestrator
from app.agents.booking.orchestrator import BookingOrchestrator

# Herramientas Core y Configuración
from app.agents.core.master_extractor import master_extractor
from app.agents.core.sanitizer import ResponseSanitizer
from app.agents.config import GREETING_KEYWORDS, SERVICE_KEYWORDS, BOOKING_KEYWORDS
from rich import print

load_dotenv()

class ValeriaMaster:
    """
    SRP: Orquestador Maestro (Router).
    Responsabilidad: Direccionar al experto basado en la intención del usuario.
    """

    def __init__(self):
        self.identity = IdentityOrchestrator()
        self.service = ServiceOrchestrator()
        self.booking = BookingOrchestrator()
        self.sanitizer = ResponseSanitizer()

    def process(self, db: Session, phone: str, message: str, history: List[Dict]):
        print(f"\n---:fireworks::fireworks: [MASTER-ROUTER] PROCESANDO MENSAJE :fireworks::fireworks:---")
                
        # 1. PRIMERO Cargar el contexto (Aquí es donde nace la variable 'state')
        state = self.identity.get_user_context(db, phone, message, history)
        state["phone"] = phone

        # 2. AHORA SÍ: Guardar lo que dijo el usuario en el historial
        if "messages" not in state or state["messages"] is None:
            state["messages"] = []
        
        # Agregamos el mensaje actual del humano al historial del estado
        state["messages"].append({"role": "user", "content": message})
        print(f"📥 [MASTER] Mensaje de usuario registrado en el historial.")

        # 3. IA: Extraer información
        extracted = master_extractor(db, message, state)
        self._sync_extracted_data(state, extracted)

        # 4. Decidir el camino
        route = self._determine_route(message, extracted.get("intent"), state)

        # 5. Delegación (Dispatch)
        # Importante: El dispatch debe devolver los mensajes actualizados con la respuesta de la IA
        raw_response, updated_messages = self._dispatch(db, state, route, message)

        # 6. Persistencia Final
        state["messages"] = updated_messages
        self.identity.save_user_context(db, phone, state)

        print(f"🏁 [MASTER] Ciclo completado.")
        return self.sanitizer.clean(raw_response), state

    def _sync_extracted_data(self, state: Dict, extracted: Dict):
        if extracted.get("date"): state["appointment_date"] = extracted["date"]
        if extracted.get("time"): state["appointment_time"] = extracted["time"]
        if extracted.get("service"): state["service_type"] = extracted["service"]

    def _determine_route(self, message: str, intent: str, state: Dict) -> str:
        msg_lower = message.lower().strip()
        user_name = state.get("user_name", "")
        
        # P1: Registro de Identidad
        if user_name == "Usuario WhatsApp" or state.get("asking_name"):
            print("👤 [MASTER] -> Redirigiendo a IDENTITY (Falta nombre)")
            return "identity"

        # P2: Saludo Explícito
        if any(greet == msg_lower for greet in GREETING_KEYWORDS):
            print(f"👋 [MASTER] -> Redirigiendo a IDENTITY (Saludo detectado)")
            return "identity"

        # P3: Consulta de Catálogo (NUEVA RUTA)
        if any(k in msg_lower for k in SERVICE_KEYWORDS):
            print(f"🛍️ [MASTER] -> Redirigiendo a SERVICE (Consulta de catálogo/precios)")
            return "service"

        # P4: Booking (Citas)   
        # Primero creas la variable booleana (True o False)
        has_booking_word = any(k in msg_lower for k in BOOKING_KEYWORDS)
        # Luego la usas en el if
        if intent == "agendar" or state.get("service_type") or has_booking_word:
            print("📅 [MASTER] -> Redirigiendo a BOOKING (Proceso de reserva)")
            return "booking"       

        # PRIORIDAD 4: Por defecto (Saludo/Catálogo)        
        print(f"🏠 [MASTER] -> No se detectó intención clara. Usando ruta por defecto: IDENTITY")
        return "identity"

    def _dispatch(self, db: Session, state: Dict, route: str, message: str) -> Tuple[str, List]:
        if route == "identity":
            return self.identity.process_welcome_flow(db, state, message)
        
        if route == "service":
            # Llamada al nuevo orquestador de servicios
            return self.service.process_service_query(db, state)

        if route == "booking":
            return self.booking.process_booking(db, state, message)

        return "Lo siento, ¿podrías repetirlo?", state.get("messages", [])