from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from app.models.clients import Client

class IdentityOrchestrator:
    """
    SRP: Gestionar la carga y persistencia del contexto del cliente en NEON.
    [cite: 2026-02-18]
    """

    def get_user_context(self, db: Session, phone: str, message: str, history: list) -> dict:
        """Recupera o crea el estado del cliente."""
        client = db.query(Client).filter(Client.phone == phone).first()
        
        if not client:
            client = Client(phone=phone, metadata_json={"messages": [], "service_type": None})
            db.add(client)
            db.commit()
            db.refresh(client)
            print(f"🆕 [IDENTITY] Nuevo cliente creado: {phone}")

        state = client.metadata_json or {}
        # Aseguramos que existan las llaves básicas
        if "messages" not in state: state["messages"] = []
        if "service_type" not in state: state["service_type"] = None
        
        print(f"✅ [IDENTITY] Contexto cargado para {phone}. Servicio actual: '{state.get('service_type')}'")
        return state

    def save_user_context(self, db: Session, phone: str, state: dict):
        """
        Guarda el estado físicamente en NEON.
        Usa flag_modified para asegurar que SQLAlchemy detecte cambios en el JSONB.
        """
        client = db.query(Client).filter(Client.phone == phone).first()
        if client:
            # Actualizamos el diccionario
            client.metadata_json = state
            
            # CRUCIAL: Forzamos a SQLAlchemy a ver el cambio interno del JSON
            flag_modified(client, "metadata_json")
            
            db.commit()
            print(f"💾 [IDENTITY] Estado persistido en NEON para {phone}")

    def process(self, db: Session, state: dict) -> str:
        """Lógica de saludo o identidad básica."""
        return "¡Hola! Soy Valeria, tu asistente virtual. ¿En qué puedo ayudarte hoy?"