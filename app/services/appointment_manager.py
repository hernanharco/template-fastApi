from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.appointments import Appointment, AppointmentStatus
from app.models.services import Service
from app.models.clients import Client
from app.schemas.appointments import AppointmentCreate
from app.services.availability import (
    is_valid_appointment_time,
    find_available_collaborator,
)


class AppointmentManager:
    """
    Clase de servicio que coordina la creación de citas.
    Aplica el principio de Responsabilidad Única (SRP) sacando la lógica pesada del router.
    """

    async def create_full_appointment(
        self, db: Session, data: AppointmentCreate
    ) -> Appointment:
        # 1. Validar que el servicio exista y esté activo
        service = (
            db.query(Service)
            .filter(Service.id == data.service_id, Service.is_active == True)
            .first()
        )
        if not service:
            raise ValueError("El servicio solicitado no existe o está inactivo.")

        # 2. Lógica de Asignación de Colaborador (Habilidades/Departamento)
        final_colab_id = data.collaborator_id
        if not final_colab_id:
            # Si no envían uno, buscamos el primero disponible que sepa hacer el servicio
            final_colab_id = find_available_collaborator(
                db, data.start_time, data.end_time, data.service_id
            )
            if not final_colab_id:
                raise ValueError(
                    "No hay profesionales disponibles para este horario y servicio."
                )

        # 3. Validar conflictos de horario (Regla de Oro: A < D y B > C)
        is_valid, error_msg = is_valid_appointment_time(
            db, final_colab_id, data.start_time, data.end_time
        )
        if not is_valid:
            raise ValueError(error_msg)

        # 4. Gestión Automática de Clientes (SaaS Flow)
        client = self._get_or_create_client(db, data)

        # 5. Crear la instancia de la Cita
        # Excluimos collaborator_id del dict porque usamos el final_colab_id calculado
        appointment_dict = data.dict(exclude={"collaborator_id"})
        new_appointment = Appointment(
            **appointment_dict,
            collaborator_id=final_colab_id,
            client_id=client.id,
            status=AppointmentStatus.SCHEDULED,
        )

        try:
            db.add(new_appointment)
            db.commit()
            db.refresh(new_appointment)
            return new_appointment
        except Exception as e:
            db.rollback()
            print(f"❌ Error en DB al crear cita: {str(e)}")
            raise Exception("No se pudo guardar la cita en la base de datos.")

    def _get_or_create_client(self, db: Session, data: AppointmentCreate) -> Client:
        """Busca un cliente por teléfono o lo crea si no existe."""
        client = None
        if data.client_phone:
            client = db.query(Client).filter(Client.phone == data.client_phone).first()

        if not client:
            client = Client(
                full_name=data.client_name,
                phone=data.client_phone,
                email=data.client_email,
            )
            db.add(client)
            db.flush()  # flush para obtener el ID sin cerrar la transacción

            # 🚀 ASIGNAR AUTOMÁTICAMENTE TODOS LOS COLABORADORES SI ES CREADO POR IA
            if data.source == "ia":
                from app.models.collaborators import Collaborator

                collaborators = (
                    db.query(Collaborator).filter(Collaborator.is_active == True).all()
                )

                for collaborator in collaborators:
                    from app.models.clients import ClientCollaborator

                    client_collab = ClientCollaborator(
                        client_id=client.id,
                        collaborator_id=collaborator.id,
                        is_favorite=False,  # Por defecto no es favorito, el cliente puede marcar después
                    )
                    db.add(client_collab)

                db.flush()
                print(
                    f"✅ Cliente {client.full_name} asignado a {len(collaborators)} colaboradores automáticamente"
                )
        else:
            # Si ya existe, actualizamos su nombre y correo por si han cambiado
            client.full_name = data.client_name
            if data.client_email:
                client.email = data.client_email

        return client


# Instancia única para ser usada en el router (Singleton pattern)
appointment_manager = AppointmentManager()
