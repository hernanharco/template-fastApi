from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.appointments import Appointment, AppointmentStatus
from app.models.clients import Client
from app.utils.availability import is_valid_appointment_time

def confirmation_node(state: dict, db: Session) -> dict:
    """
    Responsabilidad Única: Intentar persistir la cita en NEON con origen rastreable.
    [cite: 2026-02-19] Eliminada dependencia circular con graph_builder.
    """
    # 1. Recuperación de datos del estado
    date_str     = state.get("appointment_date")
    time_str     = state.get("appointment_time")
    service_id   = state.get("service_id")
    phone        = state.get("phone")
    collaborator_id = state.get("collaborator_id")
    duration     = state.get("service_duration_minutes", 60)
    
    # Manejo de origen (SaaS Modular)
    source_to_insert = state.get("source", "ia")

    # 2. Validación de datos mínimos
    if not all([date_str, time_str, service_id, phone, collaborator_id]):
        print(f"⚠️ [Confirmation] Datos insuficientes. Colab: {collaborator_id}, Phone: {phone}")
        return {**state, "confirmation_status": "missing_data"}

    try:
        # 3. NORMALIZACIÓN DE HORA
        clean_time = str(time_str).strip()
        if ":" not in clean_time:
            clean_time = f"{clean_time}:00"
        
        start_dt = datetime.strptime(f"{date_str} {clean_time[:5]}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=duration)

        # 4. VERIFICACIÓN DE DISPONIBILIDAD (SRP)
        is_valid, reason = is_valid_appointment_time(db, collaborator_id, start_dt, end_dt)
        if not is_valid:
            print(f"❌ [Confirmation] Conflicto: {reason}")
            return {**state, "confirmation_status": "conflict", "conflict_reason": reason}

        # 5. PERSISTENCIA EN NEON
        client = db.query(Client).filter(Client.phone == phone).first()
        client_name = client.full_name if client else state.get("user_name", "Usuario WhatsApp")

        appointment = Appointment(
            client_id       = client.id if client else None,
            service_id      = service_id,
            collaborator_id = collaborator_id,
            client_name     = client_name,
            client_phone    = phone,
            start_time      = start_dt,
            end_time        = end_dt,
            status          = AppointmentStatus.SCHEDULED,
            source          = source_to_insert
        )
        
        db.add(appointment)
        db.commit() 
        db.refresh(appointment)

        print(f"✅ [DB] Cita #{appointment.id} guardada exitosamente en NEON.")

        return {
            **state, 
            "confirmation_status": "confirmed", 
            "appointment_id": appointment.id,
            "appointment_time": clean_time[:5] 
        }

    except Exception as e:
        db.rollback()
        print(f"🔥 [CRITICAL DATABASE ERROR]: {str(e)}")
        return {**state, "confirmation_status": "error"}