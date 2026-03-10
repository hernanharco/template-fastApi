# CoreAppointment - Contexto de Sesión
*Fecha: 09 de marzo de 2026*

---

## 📋 Proyecto
**CoreAppointment** - Backend SaaS de agendamiento con asistente IA via WhatsApp.
- Stack: FastAPI + LangGraph + Neon PostgreSQL + Pydantic v2 + Poetry
- Asistente: "Maria" - responde por WhatsApp Business API
- Arquitectura: uvicorn (puerto 8002) → llama a langgraph dev (puerto 2024)

---

## 🏗️ Estructura del Agente
```
app/agents/
├── core/
│   └── maria_master.py       # Orquestador, llama a LangGraph via HTTP
├── nodes/
│   ├── customer_lookup_node.py
│   ├── router_node.py         # ← MODIFICADO hoy
│   ├── greeting_node.py
│   ├── catalog_node.py
│   ├── booking_node.py        # ← MODIFICADO hoy
│   ├── confirmation_node.py   # ← MODIFICADO hoy
│   └── time_parser_node.py   # ← NUEVO hoy
├── routing/
│   ├── graph.py               # ← MODIFICADO hoy
│   ├── state.py
│   └── intent.py
├── shared/
│   └── llm.py                 # ← NUEVO hoy
├── formatters/
├── memory/
├── schemas/
└── tools/
```

---

## 🔄 Flujo del Grafo
```
START → customer_lookup → router → {
    GREETING  → greeting → {WAIT→END, CATALOG}
    CATALOG   → catalog → {BOOKING, FINISH→END}
    BOOKING   → booking → {CONFIRMATION→END, CATALOG, FINISH→END}
    CONFIRMATION → confirmation → {BOOKING, CONFIRMATION→END, FINISH→END}
}
```

---

## ✅ Lo que funciona hoy

### Flujo base (sin cambios, estable)
```
Usuario: "hola"       → Maria saluda y muestra servicios
Usuario: "cejas"      → Maria muestra 2 slots disponibles (1 y 2)
Usuario: "1"          → Maria confirma la cita ✅
```

### Flujo nuevo (implementado hoy)
```
Usuario: "cejas"
Maria:   "Tengo para hoy a las 12:00 o 13:00. Responde 1 o 2"
Usuario: "otro dia"
Maria:   "¿Para qué día te gustaría? Por ejemplo: mañana, el lunes..." ✅
Usuario: "martes"
Maria:   "Tengo para Cejas el 10/03/2026 a las 09:00 o 10:00" ✅
Usuario: "1"
Maria:   "🎉 Cita agendada el 10/03/2026 a las 09:00" ✅
```

---

## 📁 Archivos Clave - Estado Actual

### `app/agents/shared/llm.py` (NUEVO)
```python
from langchain_openai import ChatOpenAI

def get_llm(temperature: float = 0.0):
    return ChatOpenAI(model="gpt-4o-mini", temperature=temperature)
```

### `app/agents/nodes/router_node.py` (MODIFICADO)
Cambio clave: regla de `active_slots` va ANTES que `selected_service_id`.
```python
# ORDEN CORRECTO:
# 1. Saludos → GREETING (resetea estado)
# 2. Si hay active_slots → siempre CONFIRMATION (maneja 1/2 y fechas)
# 3. Si hay selected_service_id → BOOKING
# 4. Default → CATALOG
```

### `app/agents/nodes/booking_node.py` (MODIFICADO)
Solo cambió una línea:
```python
# ANTES:
target_date = date.today()
# DESPUÉS:
target_date = state.get("selected_date") or date.today()
```

### `app/agents/nodes/confirmation_node.py` (MODIFICADO)
Ahora llama a `parse_time_request` cuando el usuario no responde 1 o 2:
```python
if user_text not in ["1", "2"]:
    time_result = parse_time_request(user_text)
    if time_result.get("needs_date") and time_result.get("target_date"):
        return {"selected_date": time_result["target_date"], "active_slots": [], "intent": Intent.BOOKING}
    if time_result.get("clarification_needed"):
        return {"response_text": "¿Para qué día te gustaría?...", "intent": Intent.CONFIRMATION}
    return {"response_text": "Por favor responde con 1 o 2", "intent": Intent.CONFIRMATION}
```

### `app/agents/nodes/time_parser_node.py` (NUEVO)
Función principal `parse_time_request(user_text)` con 3 capas:
1. **Keywords exactos** sin LLM: "otro dia", "otra fecha", etc. → `clarification_needed: True`
2. **Días relativos** sin LLM: "mañana", "hoy", "pasado mañana" → fecha calculada
3. **Días de semana** sin LLM: "martes", "el lunes", "para el viernes" → `_next_weekday()`
4. **LLM** como fallback: fechas específicas ("el 15 de marzo"), casos complejos

### `app/agents/routing/graph.py` (MODIFICADO)
```python
# confirmation ahora tiene edge a BOOKING (para redirigir cuando pide otro día)
workflow.add_conditional_edges(
    "confirmation",
    lambda state: state.get("intent").value if state.get("intent") else "FINISH",
    {
        "BOOKING": "booking",
        "CONFIRMATION": END,
        "FINISH": END,
    },
)
```

---

## 🚧 Pendiente / Próximo paso

### Problema conocido
"y para el sabado" falla porque el diccionario busca match exacto.
El texto tiene prefijos variables: "y para el", "y el", "quiero el", etc.

### Solución diseñada (no implementada aún)
Reemplazar el diccionario exacto por búsqueda con `in` dentro del texto:

```python
WEEKDAY_NAMES = {
    "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
    "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6,
}

def _extract_weekday(text: str) -> Optional[int]:
    normalized = text.lower().strip()
    for day_name, day_num in WEEKDAY_NAMES.items():
        if day_name in normalized:  # busca dentro, no exacto
            return day_num
    return None

# En parse_time_request, reemplazar el bloque de DAYS_OF_WEEK por:
weekday = _extract_weekday(normalized)
if weekday is not None:
    target = _next_weekday(weekday)
    return {"needs_date": True, "target_date": target, "clarification_needed": False}
```

Esto resuelve: "y para el sabado", "quiero el viernes", "me gustaría el jueves", etc.

---

## 🛠️ Comandos
```bash
poetry run poe start   # arranca uvicorn + langgraph dev juntos (UNA terminal)
poetry run poe dev     # solo uvicorn puerto 8002
poetry run poe agent   # solo langgraph dev puerto 2024
poetry run poe test    # tests
```

> ⚠️ Cada cambio en nodos requiere reiniciar `langgraph dev` (el hot-reload no siempre recarga el grafo).

---

## 💡 Aprendizajes de esta sesión
1. El código real corre en `langgraph dev`, no en uvicorn. Cambios en nodos requieren reinicio del proceso LangGraph.
2. El orden de las reglas en `router_node` es crítico: `active_slots` debe evaluarse antes que `selected_service_id`.
3. Para detección de texto en WhatsApp: diccionarios exactos + regex son más confiables que el LLM para keywords conocidos. El LLM solo para casos complejos.
4. `parse_time_request` es una función standalone reutilizable, no solo un nodo.