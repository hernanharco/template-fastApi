from sqlalchemy.orm import Session
from app.models.clients import Client
from app.agents.identity.graph_builder import create_valeria_graph


class IdentityOrchestrator:
    def __init__(self):
        self.graph = create_valeria_graph()

    def get_user_context(self, db: Session, phone: str, user_message: str, history: list):
        client = db.query(Client).filter(Client.phone == phone).first()

        service_name = None
        if client and client.current_service:
            service_name = client.current_service.name
            print(f"🧠 [Identity] Memoria recuperada: {service_name}")

        nuevo_historial = history + [{"role": "user", "content": user_message}]

        state = {
            "messages":    nuevo_historial,
            "client_name": client.full_name if client else "Usuario",
            "phone":       phone,
            "service_type": service_name,
            "current_node": "START"
        }

        final_state = self.graph.invoke(state)

        # ✅ Los nodos de identity no propagan todos los campos del state.
        # Restauramos los campos críticos que el grafo puede haber perdido.
        final_state["phone"]        = phone
        final_state["service_type"] = final_state.get("service_type") or service_name
        final_state["client_name"]  = final_state.get("client_name") or (client.full_name if client else "Usuario")

        if not client and final_state.get("client_name"):
            self._register_client(db, phone, final_state["client_name"])

        return final_state

    def _register_client(self, db: Session, phone: str, name: str):
        new_client = Client(
            full_name=name,
            phone=phone,
            source="ia",
            metadata_json={"status": "new_lead"}
        )
        db.add(new_client)
        db.commit()
        print(f"✨ [DB] Cliente {name} creado con éxito.")
    
    