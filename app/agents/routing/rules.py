import re
import logging

logger = logging.getLogger(__name__)

def check_fixed_rules(user_input: str, current_name: str):
    """
    🎯 SRP: Identificar intenciones globales (Saludos/Reinicio).
    """
    user_input = user_input.lower().strip()
    saludos = ["hola", "holaa", "buenos", "buenas", "qué tal", "que tal", "hi", "hello", "hey", "inicio"]
    
    if any(kw in user_input for kw in saludos):
        # Si ya lo conocemos, saltamos el saludo inicial y vamos al catálogo
        if current_name != "Nuevo Cliente":
            return "CATALOG"
        return "GREETING"
    return None

def check_selection_rules(user_input: str, shown_ids: list, active_slots: list, services_metadata: list = None):
    """
    🎯 SRP: Mapear la entrada a una selección de Servicio o de Turno.
    Soporta: Números (1-9), Nombres (Corte) y Horas (12:00).
    """
    user_input = user_input.lower().strip()
    normalized_input = user_input.replace(".", ":")

    # 1. Prioridad: ¿Es una hora exacta de los slots mostrados?
    if active_slots:
        for slot in active_slots:
            slot_time = slot.get("time", "")
            # Coincidencia exacta (12:00) o parcial (12)
            if normalized_input == slot_time or (len(normalized_input) >= 2 and normalized_input in slot_time):
                return "CONFIRMATION"

    # 2. ¿Es un nombre de servicio? (Fuzzy Match manual con metadata)
    # Evitamos esto si el usuario escribió un número claro (ej: "la 1")
    if services_metadata and not re.search(r"\b([1-9]|10)\b", user_input):
        for item in services_metadata:
            try:
                # item viene como "ID 8: Corte de Cabello"
                parts = item.split(": ")
                s_id = int(parts[0].replace("ID ", ""))
                s_name = parts[1].lower()
                
                # Si el usuario escribió "corte" y está en "corte de cabello"
                if len(user_input) > 3 and (user_input in s_name or s_name in user_input):
                    return ("BOOKING", s_id)
            except Exception:
                continue

    # 3. Lógica de números (1, 2, 3...) y ordinales (primero, segundo)
    ordinals = {"primera": 1, "primero": 1, "segunda": 2, "segundo": 2, "tercera": 3, "tercer": 3}
    selected_index = None
    
    match_number = re.search(r"\b([1-9]|10)\b", user_input)
    if match_number:
        selected_index = int(match_number.group(1)) - 1
    else:
        for word, val in ordinals.items():
            if word in user_input:
                selected_index = val - 1
                break

    # Mapeo final del índice detectado
    if selected_index is not None:
        # Si hay turnos en pantalla, el número se refiere al turno
        if active_slots and 0 <= selected_index < len(active_slots):
            return "CONFIRMATION"
        
        # Si hay servicios en pantalla, el número se refiere al servicio
        if shown_ids and 0 <= selected_index < len(shown_ids):
            return ("BOOKING", shown_ids[selected_index])
            
    return None

def check_temporal_rules(user_input: str):
    """
    🎯 SRP: Detectar días, horas o filtros temporales (ej: 'después de las 3').
    """
    user_input = user_input.lower().strip()
    
    # 1. Palabras clave de días
    date_keywords = ["hoy", "mañana", "lunes", "martes", "miercoles", "miércoles", 
                     "jueves", "viernes", "sabado", "sábado", "domingo", "otro día"]
    
    if any(dk in user_input for dk in date_keywords):
        return "BOOKING"

    # 2. Filtros de rango (Mantienen al usuario en el nodo de búsqueda/BOOKING)
    filtros_rango = ["despues de", "antes de", "a partir de", "luego de", "más tarde de"]
    if any(f in user_input for f in filtros_rango):
        return "BOOKING"

    # 3. 🌟 SELECCIÓN POR EXTREMOS (Saltan a CONFIRMATION porque ya es una elección)
    
    # Conceptos de "Lo más tarde posible"
    tarde_keywords = ["ultima hora", "última hora", "el ultimo", "la última", "lo más tarde"]
    if any(c in user_input for c in tarde_keywords):
        return "CONFIRMATION"

    # Conceptos de "Lo más temprano posible"
    temprano_keywords = ["primera hora", "lo más temprano", "el primero", "la primera", "abren", "madrugar"]
    if any(c in user_input for c in temprano_keywords):
        return "CONFIRMATION"

    # 4. Regex para horas exactas (12:00, 3pm, etc.)
    time_pattern = r"(\b[0-1]?[0-9]|2[0-3])([:.]?[0-5][0-9])?\s*(am|pm|de la tarde|de la mañana)?\b"
    if re.search(time_pattern, user_input) and len(user_input) < 25:
        return "CONFIRMATION"
        
    return None

async def evaluate_all_rules(user_input: str, current_name: str, shown_ids: list, active_slots: list, services_metadata: list = None):
    """
    🚀 Orquestador: Filtra la entrada por todas las reglas antes de ir a la IA.
    Retorna (action, id_o_none).
    """
    # 1. Reglas de Saludo/Sistema
    action = check_fixed_rules(user_input, current_name)
    if action: return action, None

    # 2. Reglas de Selección (La más importante para evitar errores de ID)
    result = check_selection_rules(user_input, shown_ids, active_slots, services_metadata)
    if result:
        if isinstance(result, tuple): return result # Retorna ("BOOKING", 8)
        return result, None # Retorna "CONFIRMATION" o "CATALOG"

    # 3. Reglas de tiempo
    action = check_temporal_rules(user_input)
    if action: return action, None

    return None, None