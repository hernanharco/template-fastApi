import os
from datetime import datetime
from typing import List, Tuple, Dict
from dotenv import load_dotenv
from sqlalchemy.orm import Session

# Orquestadores de Dominio (SRP)
from app.agents.identity.orchestrator import IdentityOrchestrator
from app.agents.service.orchestrator import ServiceOrchestrator
from app.agents.booking.orchestrator import BookingOrchestrator

# Core Tools y Lógica de Negocio
from app.agents.core.master_extractor import master_extractor
from app.agents.core.sanitizer import ResponseSanitizer 
from app.agents.booking.fuzzy_logic import service_fuzzy_match

load_dotenv()

class ValeriaMaster:
    """
    SRP: Orquestador Maestro (Root).
    [cite: 2026-02-18] Centraliza la lógica multi-tenant y garantiza que 
    la persistencia en NEON sea siempre con nombres oficiales.
    """

    def __init__(self):
        self.identity = IdentityOrchestrator()
        self.service = ServiceOrchestrator()
        self.booking = BookingOrchestrator()
        self.sanitizer = ResponseSanitizer()

    def process(self, db: Session, phone: str, message: str, history: List[Dict]):
        """
        Punto de entrada principal. Gestiona la carga, limpieza, 
        procesamiento y persistencia del contexto del usuario.
        """
        print(f"\n--- ⚡ [MASTER] PROCESANDO MENSAJE ---")
        
        # 1. Recuperar contexto desde NEON
        state = self.identity.get_user_context(db, phone, message, history)
        self._enforce_time_window(state)
        
        # 2. LIMPIEZA DE ESTADO PREVIO (Normalización inmediata)
        if state.get("service_type"):
            match_state = service_fuzzy_match(db, state["service_type"])
            if match_state:
                state["service_type"] = match_state[0]
                state["service_id"] = match_state[1]

        # 3. Extracción de nueva información con IA
        extracted = master_extractor(db, message, state)
        intent = str(extracted.get("intent", "unknown")).lower()
        
        # 4. Normalizar lo que la IA detectó en este mensaje nuevo
        service_raw = extracted.get("service")
        if service_raw:
            match_new = service_fuzzy_match(db, service_raw)
            if match_new:
                state["service_type"] = match_new[0]
                state["service_id"] = match_new[1]
                print(f"✨ [MASTER] Servicio normalizado: {match_new[0]}")
            else:
                if not state.get("service_type"):
                    state["service_type"] = service_raw

        # 5. Determinar la ruta (Lógica corregida para evitar bucles)
        final_route = self._determine_smart_route(message, intent, state)
        
        # 6. Ejecución (Dispatch)
        raw_response, updated_messages = self._dispatch(db, state, final_route, message)
        
        # 7. Persistencia final en NEON con last_updated [cite: 2026-02-18]
        state["messages"] = updated_messages
        state["last_updated"] = datetime.now().isoformat()
        self.identity.save_user_context(db, phone, state)

        return self.sanitizer.clean(raw_response), state

    def _enforce_time_window(self, state: Dict):
        """Limpia el contexto si pasaron más de 4 horas."""
        last_str = state.get("last_updated")
        if last_str:
            last_dt = datetime.fromisoformat(last_str)
            if (datetime.now() - last_dt).total_seconds() > 14400:
                state["service_type"] = None

    def _determine_smart_route(self, message: str, intent: str, state: Dict) -> str:
        """
        SRP: Lógica de decisión de rutas. 
        Ajustado para evitar que el flujo de reserva regrese a 'saludo'.
        """
        msg = message.lower().strip()
        ya_tiene_servicio = state.get("service_type") is not None
        
        # 1. Saludos puros (Solo si el mensaje es corto y es un saludo claro)
        saludos = ["hola", "buenas", "hey", "buenos dias"]
        if msg in saludos or (intent == "saludo" and len(msg.split()) < 3):
            return "saludo"

        # 2. Si ya tenemos un servicio, priorizamos seguir agendando
        if ya_tiene_servicio:
            # Si quiere ver catálogo explícitamente, lo dejamos cambiar
            if intent in ["ver_catalogo", "catalog"]:
                return "ver_catalogo"
            # De lo contrario, cualquier mensaje (fecha, confirmación, duda) va a Booking
            return "agendar"

        # 3. Si quiere agendar pero no hay servicio en el estado
        if intent == "agendar" and not ya_tiene_servicio:
            return "ver_catalogo"

        # 4. Intenciones directas
        if intent in ["ver_catalogo", "catalog"]: return "ver_catalogo"
        if intent == "agendar": return "agendar"
        
        return "saludo"

    def _determine_final_route(self, message: str, intent: str, state: Dict) -> str:
        """Alias para compatibilidad con TestMasterLogic."""
        return self._determine_smart_route(message, intent, state)

    def _dispatch(self, db: Session, state: Dict, route: str, raw_message: str) -> Tuple[str, List]:
        if route == "agendar":
            return self.booking.process_booking(db, state, raw_message)

        if route in ["saludo", "ver_catalogo"]:
            saludo = self.identity.process(db, state)
            catalog_summary = self.service.get_catalog_summary(db) 
            res = f"{saludo}\n\nActualmente ofrecemos:\n{catalog_summary}\n\n¿Te gustaría agendar alguno?"
            
            msgs = state.get("messages", [])
            msgs.append({"role": "assistant", "content": res})
            return res, msgs

        return self.service.process_service(db, state)