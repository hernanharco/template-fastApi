from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime, timedelta
from app.models.clients import Client


class IdentityOrchestrator:
    """
    SRP: Gestionar identidad y flujos de bienvenida/registro.
    Responsabilidad: Asegurar un estado limpio y persistencia en NEON (JSONB).
    """

    def get_user_context(
        self, db: Session, phone: str, message: str, history: list
    ) -> dict:
        """
        Recupera el contexto desde la columna metadata_json de NEON.
        """
        client = db.query(Client).filter(Client.phone == phone).first()

        if not client:
            # Si no existe, creamos el registro con valores por defecto
            client = Client(
                phone=phone,
                full_name="Usuario WhatsApp",
                business_id=1,
                source="ia",
                metadata_json={
                    "messages": [],
                    "last_updated": datetime.now().isoformat(),
                },
            )
            db.add(client)
            db.commit()
            db.refresh(client)
            print(f"🆕 [IDENTITY] Nuevo cliente registrado en NEON: {phone}")

        state = client.metadata_json or {}
        state["user_name"] = client.full_name
        state["phone"] = phone  # Aseguramos que el teléfono esté en el estado

        # Lógica de Reset por inactividad (30 min)
        should_reset = True
        last_upd_str = state.get("last_updated")
        if last_upd_str:
            try:
                if datetime.now() - datetime.fromisoformat(last_upd_str) < timedelta(
                    minutes=30
                ):
                    should_reset = False
            except:
                pass

        # Campos base que garantizan que el JSONB tenga estructura
        base_state = {
            "messages": [],
            "service_type": None,
            "service_id": None,
            "appointment_time": None,
            "appointment_date": None,
            "asking_name": False,
            "booking_confirmed": False,
            "collaborator_id": None,
            "service_duration_minutes": None,
        }

        for key, value in base_state.items():
            if should_reset or key not in state:
                state[key] = value

        return state

    def process_welcome_flow(
        self, db: Session, state: dict, message: str
    ) -> tuple[str, list]:
        """
        SRP: Orquesta el saludo y LIMPIA el metadata_json para iniciar de cero.
        """
        print(f"\n--- 👤 [ORCH-IDENTITY] Iniciando Orquestación ---")
        print(f"MENSAJE RECIBIDO: {message}")
        from app.agents.service.orchestrator import ServiceOrchestrator

        service_agent = ServiceOrchestrator()

        # 1. 🔥 LIMPIEZA TOTAL del 'cajón' metadata_json
        # Borramos historial viejo y datos de citas previas
        self._clear_all_context_data(state)

        # 2. Iniciamos historial nuevo
        new_messages = []

        # 3. LÓGICA DE RESPUESTA
        if state.get("user_name") == "Usuario WhatsApp" or state.get("asking_name"):
            if not state.get("asking_name"):
                res = "¡Hola! Soy Valeria. Antes de comenzar, ¿me podrías decir tu nombre completo?"
                state["asking_name"] = True
            else:
                full_name = message.strip()
                state["user_name"] = full_name
                state["asking_name"] = False
                self.update_client_name(db, state["phone"], full_name)

                catalog = service_agent.get_catalog_summary(db)
                res = f"¡Mucho gusto, {full_name}! Gracias por registrarte. Actualmente ofrecemos:\n{catalog}\n\n¿Cuál te gustaría agendar?"
        else:
            user_name = state.get("user_name")
            catalog = service_agent.get_catalog_summary(db)
            res = f"¡Hola, {user_name}! Qué gusto saludarte de nuevo. ¿Qué servicio te gustaría agendar hoy?\n\n{catalog}"

        # 4. Sincronizamos el estado con el nuevo mensaje únicamente
        new_messages.append({"role": "assistant", "content": res})
        state["messages"] = new_messages

        return res, new_messages

    def _clear_all_context_data(self, state: dict):
        """
        Limpia las llaves del diccionario para que al guardar en NEON el JSON esté vacío.
        """
        keys_to_reset = [
            "service_type",
            "service_id",
            "appointment_time",
            "appointment_date",
            "booking_confirmed",
            "collaborator_id",
            "service_duration_minutes",
            "current_service_id",
        ]

        for key in keys_to_reset:
            state[key] = None

        state["messages"] = []  # Vaciamos el historial de texto
        print("🧹 [IDENTITY] metadata_json limpiado en memoria.")

    def update_client_name(self, db: Session, phone: str, new_name: str):
        """Actualiza la columna full_name en NEON."""
        client = db.query(Client).filter(Client.phone == phone).first()
        if client:
            client.full_name = new_name
            db.commit()
            print(f"✅ [NEON] Columna 'full_name' actualizada a: {new_name}")

    def save_user_context(self, db: Session, phone: str, state: dict):
        """
        Persistencia final: Toma el diccionario 'state' y lo guarda en la columna JSONB.
        """
        client = db.query(Client).filter(Client.phone == phone).first()
        if client:
            state["last_updated"] = datetime.now().isoformat()

            # Sincronizamos el nombre por si acaso
            if "user_name" in state:
                client.full_name = state["user_name"]

            # Guardamos el diccionario completo en la columna metadata_json
            client.metadata_json = state

            # Obligatorio para que SQLAlchemy detecte cambios en JSONB
            flag_modified(client, "metadata_json")

            db.commit()
            print(f"💾 [NEON] metadata_json persistido con éxito para {phone}")
