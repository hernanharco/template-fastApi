# app/agents/booking/booking_node.py
import traceback
from datetime import datetime, date, timedelta
from langchain_core.messages import AIMessage
from rich import print as rprint

from app.db.session import SessionLocal
from app.agents.state import AgentState
from app.services.availability import get_available_slots
from app.agents.booking.extractor_booking import extract_booking_intent
from app.agents.booking.fuzzy_logic import service_fuzzy_match

# --- FUNCIONES INTERNAS DE APOYO ---

def filtrar_y_espaciar_slots(all_slots, intent_data):
    """
    SRP: Filtra por jornada y por límites específicos (operadores mayor_que/menor_que).
    """
    if not all_slots: 
        return []

    pref = intent_data.get("preferencia", "indiferente")
    limite_str = intent_data.get("hora_limite") # Ej: "11:30"
    operador = intent_data.get("operador")      # Ej: "mayor_que"

    slots_base = all_slots

    # 1. FILTRADO POR JORNADA (Mañana / Tarde)
    if pref == "tarde":
        slots_base = [s for s in all_slots if s["start_time"].hour >= 12]
    elif pref == "manana":
        slots_base = [s for s in all_slots if s["start_time"].hour < 12]

    # 2. 🚀 EL PARCHE: Filtro de Precisión (Antes de / Después de)
    if limite_str and operador:
        try:
            # Convertimos el string "HH:MM" a objeto time para comparar
            limite_time = datetime.strptime(limite_str, "%H:%M").time()
            
            if operador == "mayor_que":
                slots_base = [s for s in slots_base if s["start_time"].time() >= limite_time]
            elif operador == "menor_que":
                slots_base = [s for s in slots_base if s["start_time"].time() <= limite_time]
            elif operador == "exacto":
                slots_base = [s for s in slots_base if s["start_time"].time() == limite_time]
        except Exception as e:
            rprint(f"[bold red]⚠️ Error procesando hora_limite: {e}[/bold red]")

    if not slots_base:
        return []

    # 3. SELECCIONAR OPCIONES CON ESPACIADO (Evitar mostrar todo pegado)
    finales = []
    finales.append(slots_base[0])
    
    # Intentamos buscar una segunda opción que esté al menos 1 hora después
    h_objetivo = slots_base[0]["start_time"] + timedelta(hours=1)
    for s in slots_base:
        if s["start_time"] >= h_objetivo:
            finales.append(s)
            break
                
    return finales

# --- NODO PRINCIPAL ---

def booking_expert_node(state: AgentState) -> dict:
    rprint("\n[bold cyan]🔍 --- BOOKING NODE START ---[/bold cyan]")
    db = SessionLocal()
    
    try:
        messages = state.get("messages", [])
        user_msg = str(messages[-1].content) if messages else ""
        history_text = state.get("history_text", "")
        service_id = state.get("service_id")
        
        # 1. Identificar servicio si no viene en el estado
        if not service_id:
            match = service_fuzzy_match(db, user_msg)
            if match:
                _, service_id = match
            else:
                return {
                    "messages": [AIMessage(content="¡Claro! Pero dime, ¿para qué servicio te gustaría agendar? 💇‍♀️")],
                    "current_node": "booking_expert"
                }

        # 2. Extraer intención con el nuevo parche de hora_limite
        intent = extract_booking_intent(user_msg, history_text)
        
        # Validar fecha (no reservar en el pasado)
        original_query_date = datetime.strptime(intent["date"], "%Y-%m-%d").date()
        if original_query_date < date.today(): 
            original_query_date = date.today()

        # 3. BÚSQUEDA PROACTIVA (Máximo 3 días de adelanto)
        opciones = []
        fecha_a_consultar = original_query_date
        intentos = 0

        while intentos < 3:
            all_slots = get_available_slots(db, fecha_a_consultar, service_id)
            
            # 🚀 Pasamos todo el 'intent' para filtrar por operador
            opciones = filtrar_y_espaciar_slots(all_slots, intent)
            
            if opciones: 
                break
            
            fecha_a_consultar += timedelta(days=1)
            intentos += 1
            rprint(f"[yellow]DEBUG: {fecha_a_consultar - timedelta(days=1)} sin cupo ajustado, probando {fecha_a_consultar}[/yellow]")

        # 4. Caso: No hay disponibilidad
        if not opciones:
            return {
                "messages": [AIMessage(content=f"Vaya, para esa hora no me queda nada libre pronto. 😅 ¿Probamos otro día o una hora distinta?")],
                "current_node": "booking_expert",
                "service_id": service_id
            }

        # 5. CONSTRUIR RESPUESTA DINÁMICA
        fecha_fmt = fecha_a_consultar.strftime("%d/%m/%Y")
        
        # Construimos el texto según lo que pidió el usuario (Confirmación activa)
        contexto_hora = ""
        if intent.get("hora_limite"):
            prefix = "después de las" if intent["operador"] == "mayor_que" else "antes de las"
            contexto_hora = f" {prefix} {intent['hora_limite']}"
        elif intent.get("preferencia") != "indiferente":
            contexto_hora = f" para la {intent['preferencia']}"

        res_text = f"¡Perfecto! Para el *{fecha_fmt}*{contexto_hora} tengo estos espacios:\n\n"

        for i, s in enumerate(opciones, 1):
            res_text += f"{i}️⃣ {s['start_time'].strftime('%H:%M')}\n"
        
        res_text += "\n¿Cuál te queda mejor?"

        return {
            "messages": [AIMessage(content=res_text)],
            "current_node": "booking_expert",
            "service_id": service_id,
            "last_updated": datetime.now().isoformat()
        }

    except Exception as e:
        rprint(f"[bold red]❌ Error en Nodo Booking:[/bold red]\n{traceback.format_exc()}")
        return {
            "messages": [AIMessage(content="Ups, me lie un poco con la agenda. ¿Me repites qué día y hora buscabas? 😅")], 
            "current_node": "booking_expert"
        }
    finally:
        db.close()
        rprint("[bold cyan]🔍 --- BOOKING NODE END ---[/bold cyan]\n")