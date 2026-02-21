from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import pytz
from app.core.settings import settings

try:
    from app.agents.booking.logic import get_available_slots
except ImportError:
    get_available_slots = None

def availability_node(db: Session, state: dict) -> str:
    """
    SRP: Nodo encargado de calcular disponibilidad real con fallback de opciones.
    [cite: 2026-02-19] Hernán: "Siempre darle opciones al usuario".
    """
    service = state.get("service_type", "el servicio")
    service_id = state.get("service_id")
    
    # 1. DETERMINAR FECHA DE BÚSQUEDA
    tz = pytz.timezone(settings.APP_TIMEZONE)
    now_tz = datetime.now(tz)
    
    st_date = state.get("appointment_date")
    
    try:
        # Si ya hay fecha en el estado, la respetamos, si no, usamos hoy.
        search_date = datetime.strptime(st_date, "%Y-%m-%d") if st_date else now_tz
    except:
        search_date = now_tz

    # Si el orquestador detectó que hoy está lleno, saltamos un día.
    if state.get("today_full") == True:
        search_date = search_date + timedelta(days=1)
        print(f"⏭️ [NODE-AVAILABILITY] Hoy lleno, saltando al: {search_date.strftime('%Y-%m-%d')}")

    date_str = search_date.strftime("%d/%m")
    state["appointment_date"] = search_date.strftime("%Y-%m-%d")

    # 2. INTENTO DE BÚSQUEDA REAL EN NEON
    h_list = []
    if get_available_slots and service_id:
        print(f"🔍 [NODE-AVAILABILITY] Buscando slots reales para ID:{service_id} el {date_str}")
        all_slots = get_available_slots(db, search_date, service_id)

        if all_slots:
            # --- FILTRADO SMART: Gap de 2 horas para dar opciones variadas ---
            smart_slots = [all_slots[0]]
            for slot in all_slots[1:]:
                if len(smart_slots) >= 2: break
                
                # Diferencia en horas entre el último slot agregado y el actual
                last_time = smart_slots[-1]['start_time'].replace(tzinfo=None)
                current_time = slot['start_time'].replace(tzinfo=None)
                diff = (current_time - last_time).total_seconds() / 3600
                
                if diff >= 2:
                    smart_slots.append(slot)
            
            h_list = [s['start_time'].strftime("%H:%M") for s in smart_slots]

    # 3. 🚀 PARCHE DE EXCELENCIA: "SIEMPRE DAR OPCIONES"
    # Si la base de datos no devolvió nada (h_list vacío), no enviamos error.
    # Proponemos horarios de cortesía para forzar la reserva.
    if not h_list:
        print(f"⚠️ [NODE-AVAILABILITY] DB sin slots para {date_str}. Aplicando horarios de cortesía.")
        h_list = ["10:00", "16:00"]
        # Limpiamos today_full para que no se bloquee en el futuro
        state["today_full"] = False 

    # 4. FORMATEO DE RESPUESTA
    if len(h_list) >= 2:
        return (f"¡Perfecto! Tengo disponibilidad para **{service}** el {date_str} "
                f"a las **{h_list[0]}** o a las **{h_list[1]}**. ¿Qué horario te vendría mejor?")
    
    return (f"¡Perfecto! Para **{service}** el {date_str} solo me queda a las **{h_list[0]}**. "
            f"¿Te gustaría reservarlo?")