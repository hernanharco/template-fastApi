from sqlalchemy.orm import Session
from app.models.clients import Client
from app.agents.identity.graph_builder import create_valeria_graph

class IdentityOrchestrator:
    def __init__(self):
        self.graph = create_valeria_graph()

    def get_user_context(self, db: Session, phone: str, user_message: str, history: list):
        client = db.query(Client).filter(Client.phone == phone).first()

        # Un cliente es "genérico" si no existe o si su nombre es "Usuario"
        is_generic = not client or client.full_name in ["Usuario", "Cliente", None]

        service_name = None
        if client and client.current_service_id: # Usamos ID para evitar errores de relación
            from app.models.services import Service
            srv = db.query(Service).filter(Service.id == client.current_service_id).first()
            if srv: service_name = srv.name

        nuevo_historial = history + [{"role": "user", "content": user_message}]

        state = {
            "messages":     nuevo_historial,
            "client_name":  client.full_name if client else "Usuario",
            "phone":        phone,
            "service_type": service_name,
            "is_new_client": is_generic 
        }

        final_state = self.graph.invoke(state)
        extracted_name = final_state.get("client_name")
        
        # --- CAMBIO CLAVE: Lógica de Persistencia ---
        has_real_name = extracted_name and extracted_name.lower() not in ["usuario", "cliente", "none"]

        if not client:
            if has_real_name:
                # Si dijo su nombre, lo creamos de una vez bien
                self._register_client(db, phone, extracted_name)
                final_state["is_new_client"] = False
            else:
                # Si no hay nombre, NO lo creamos en DB.
                # Mantenemos el flag en True para que Valeria pregunte.
                final_state["is_new_client"] = True
        
        elif is_generic and has_real_name:
            # Si ya existía como "Usuario", ahora lo actualizamos a su nombre real
            client.full_name = extracted_name
            db.commit()
            print(f"📝 [DB] Nombre actualizado físicamente: {extracted_name}")
            final_state["is_new_client"] = False

        return final_state

    def _register_client(self, db: Session, phone: str, name: str):
        new_client = Client(
            full_name=name,
            phone=phone,
            source="ia",
            metadata_json={"status": "new_lead"}
        )
        db.add(new_client)
        try:
            db.commit()
            print(f"✨ [DB] Cliente {name} creado con éxito.")
        except Exception as e:
            db.rollback()
            print(f"❌ [DB] Error al registrar: {e}")