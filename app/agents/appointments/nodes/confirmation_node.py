from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.appointments import Appointment, AppointmentStatus, AppointmentSource
from app.models.clients import Client
from app.utils.availability import find_available_collaborator, is_valid_appointment_time

def confirmation_node(state: dict, db: Session) -> dict:
    """
    Responsabilidad Única: Intentar persistir la cita en NEON con origen rastreable.
    """
    # 1. Recuperación de datos del estado
    date_str     = state.get("appointment_date")
    time_str     = state.get("appointment_time")
    service_id   = state.get("service_id")
    phone        = state.get("phone")
    duration     = state.get("service_duration_minutes", 60)
    
    # 🤖 Seguridad de Origen: 
    # Extraemos el valor string ("ia", "manual", etc.) para que Neon lo acepte sin errores.
    raw_source = state.get("source", "manual")
    # Si viene como objeto Enum, extraemos su valor. Si es string, lo usamos directo.
    source_to_insert = raw_source.value if hasattr(raw_source, 'value') else raw_source

    # 2. Validación de datos mínimos
    if not all([date_str, time_str, service_id, phone]):
        print(f"⚠️ [Confirmation] Datos insuficientes")
        return {**state, "confirmation_status": "missing_data"}

    try:
        # 3. NORMALIZACIÓN DE HORA
        clean_time = str(time_str).strip()
        if ":" not in clean_time:
            clean_time = f"{clean_time}:00"
        
        # Tomamos solo HH:MM para evitar errores de formato largo
        start_dt = datetime.strptime(f"{date_str} {clean_time[:5]}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=duration)

        # 4. VERIFICACIÓN DE DISPONIBILIDAD (SRP)
        collaborator_id = find_available_collaborator(db, start_dt, end_dt, service_id)
        if not collaborator_id:
            print(f"❌ [Confirmation] No hay colaboradores disponibles")
            return {**state, "confirmation_status": "no_collaborator"}

        is_valid, reason = is_valid_appointment_time(db, collaborator_id, start_dt, end_dt)
        if not is_valid:
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
            source          = source_to_insert # 👈 Aquí se inserta "ia" limpiamente
        )
        
        db.add(appointment)
        db.commit() 
        db.refresh(appointment)

        print(f"✅ [DB] Cita #{appointment.id} [Origen: {source_to_insert}] guardada exitosamente.")

        return {
            **state, 
            "confirmation_status": "confirmed", 
            "appointment_id": appointment.id,
            "appointment_time": clean_time 
        }

    except Exception as e:
        db.rollback()
        print(f"🔥 [CRITICAL DATABASE ERROR]: {str(e)}")
        return {**state, "confirmation_status": "error"}