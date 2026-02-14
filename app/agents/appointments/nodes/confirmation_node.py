"""
ConfirmationNode — Dominio: Appointments
Responsabilidad única: persistir la cita en PostgreSQL.
No responde, no decide el flujo, no valida negocio más allá de disponibilidad.
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.appointments import Appointment, AppointmentStatus
from app.models.clients import Client
from app.utils.availability import find_available_collaborator, is_valid_appointment_time


def confirmation_node(state: dict, db: Session) -> dict:
    date_str     = state.get("appointment_date")
    time_str     = state.get("appointment_time")
    service_id   = state.get("service_id")
    service_name = state.get("service_type", "")
    phone        = state.get("phone")
    duration     = state.get("service_duration_minutes", 60)

    if not all([date_str, time_str, service_id, phone]):
        print(f"⚠️ [Confirmation] Faltan datos: date={date_str} time={time_str} service={service_id} phone={phone}")
        # ✅ {**state} para no perder contexto en el grafo
        return {**state, "confirmation_status": "missing_data"}

    try:
        start_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        end_dt   = start_dt + timedelta(minutes=duration)

        collaborator_id = find_available_collaborator(db, start_dt, end_dt, service_id)
        if not collaborator_id:
            return {**state, "confirmation_status": "no_collaborator"}

        is_valid, reason = is_valid_appointment_time(db, collaborator_id, start_dt, end_dt)
        if not is_valid:
            return {**state, "confirmation_status": "conflict", "conflict_reason": reason}

        client      = db.query(Client).filter(Client.phone == phone).first()
        client_name = client.full_name if client else "Cliente"
        client_id   = client.id if client else None

        appointment = Appointment(
            client_id       = client_id,
            service_id      = service_id,
            collaborator_id = collaborator_id,
            client_name     = client_name,
            client_phone    = phone,
            start_time      = start_dt,
            end_time        = end_dt,
            status          = AppointmentStatus.SCHEDULED,
        )
        db.add(appointment)
        db.commit()
        db.refresh(appointment)

        print(f"✅ [DB] Cita #{appointment.id} — {client_name} | {service_name} | {start_dt}")

        return {**state, "confirmation_status": "confirmed", "appointment_id": appointment.id}

    except Exception as e:
        db.rollback()
        print(f"❌ [confirmation_node] Error: {e}")
        return {**state, "confirmation_status": "error"}