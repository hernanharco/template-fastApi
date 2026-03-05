# 🔧 FLUJO DE AGENTES CORREGIDO - Instrucciones de Prueba

## 🚨 **PROBLEMAS IDENTIFICADOS Y CORREGIDOS**

### **1. KeyError 'GREETING' - CORREGIDO ✅**
- **Causa**: El nodo `catalog` devolvía `"next_action": "GREETING"` pero el edge no tenía esta ruta
- **Solución**: Añadida ruta `"GREETING": "greeting"` en todos los edges necesarios

### **2. Bucle Infinito - CORREGIDO ✅**
- **Causa**: Clientes existentes con "hola" iban a `greeting` en lugar de `catalog`
- **Solución**: Detección de saludos contextuales

### **3. Flujo Incorrecto - CORREGIDO ✅**
- **Causa**: Router siempre devolvía `"GREETING"` al final
- **Solución**: Lógica específica para clientes existentes

---

## 🎯 **CAMBIOS REALIZADOS**

### **Archivo: `app/agents/routing/graph.py`**
```python
# Edge de catalog - AHORA COMPLETO
workflow.add_conditional_edges(
    "catalog",
    lambda state: state.get("next_action"),
    {
        "FINISH": END,
        "BOOKING": "booking",
        "GREETING": "greeting",     # 🚀 AÑADIDO
    },
)

# Edge de booking - AHORA COMPLETO
workflow.add_conditional_edges(
    "booking",
    lambda state: state.get("next_action"),
    {
        "CONFIRM": "appointments",
        "CONFIRMATION": "appointments",  # 🚀 AÑADIDO
        "FINISH": END,
        "CATALOG": "catalog",
        "GREETING": "greeting",          # 🚀 AÑADIDO
    },
)
```

### **Archivo: `app/agents/routing/nodes.py`**
```python
# 🚀 DETECCIÓN DE SALUDOS (para clientes existentes)
saludo_keywords = ["hola", "holaa", "buenos", "buenas", "qué tal", "que tal", "hi", "hello", "hey"]
if any(kw in user_input_lower for kw in saludo_keywords):
    # Si el cliente ya existe, va directo a catálogo
    if current_name != "Nuevo Cliente":
        rprint(f"[green]✅ Saludo de cliente existente → catalog[/green]")
        return {"next_action": "CATALOG"}
    # Si es nuevo, va a greeting para pedir nombre
    return {"next_action": "GREETING"}

# 4. CLIENTE EXISTENTE: Por defecto va a catálogo
if current_name != "Nuevo Cliente":
    return {"next_action": "CATALOG"}
```

---

## 🔄 **FLUJO ESPERADO CORREGIDO**

### **Cliente Existente (Hernán)**
```
👤 "hola"
🔍 customer_lookup: "Hernán" encontrado
🚦 router: Saludo de cliente existente → CATALOG
📚 catalog: Muestra servicios + guarda shown_service_ids
👤 "corte de cabello"
🔍 catalog: Detecta "corte" → ID=2 → BOOKING
📅 booking: Muestra horarios para corte
👤 "11.00"
📅 booking: Selección → CONFIRM → appointments
✅ appointments: Agenda cita → END
🎊 FIN
```

### **Cliente Nuevo**
```
👤 "hola"
🔍 customer_lookup: No existe → "Nuevo Cliente"
🚦 router: Saludo de cliente nuevo → GREETING
👋 greeting: "¿Cuál es tu nombre?"
👤 "Juan"
🚦 router: Nombre detectado → update_client + GREETING
👋 greeting: "¡Gracias Juan! Aquí tienes nuestros servicios"
📚 catalog: Muestra servicios
... (continúa flujo normal)
```

---

## 🧪 **INSTRUCCIONES PARA PROBAR**

### **1. Reiniciar Servidor**
```bash
# Detener servidor actual (CTRL+C)
# Limpiar caché
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# Iniciar servidor
poetry run poe dev
```

### **2. Probar Flujo Esperado**

#### **Caso 1: Cliente Existente (Hernán)**
```
📱 WhatsApp: "hola"
🤖 Esperado: Catálogo de servicios (9 opciones)
📱 WhatsApp: "corte de cabello"  
🤖 Esperado: Horarios disponibles (11:00, 12:00)
📱 WhatsApp: "11.00" o "1"
🤖 Esperado: Confirmación de cita agendada
🎊 FIN
```

#### **Caso 2: Cliente Nuevo**
```
📱 WhatsApp: "hola"
🤖 Esperado: "¿Cuál es tu nombre?"
📱 WhatsApp: "Pedro"
🤖 Esperado: "¡Gracias Pedro! Catálogo de servicios"
📱 WhatsApp: "2" (manicure)
🤖 Esperado: Horarios para manicure
... (continúa)
```

### **3. Verificar Logs**

**Busca estos mensajes en la consola:**
```
✅ Cliente encontrado: Hernán
✅ Saludo de cliente existente → catalog
✅ Servicio identificado: 2
✅ Cita agendada exitosamente
```

**NO deberías ver:**
```
❌ KeyError: 'GREETING'
🔄 Bucle infinito de saludos
```

---

## 🚨 **SI EL ERROR PERSISTE**

### **Opción 1: Verificar Importaciones**
```python
# En app/api/v1/endpoints/ai_whatsapp.py
# Asegúrate que importe el grafo correcto:
from app.agents.routing.graph import graph
```

### **Opción 2: Forzar Recarga Completa**
```bash
# Reiniciar completamente
pkill -f uvicorn
poetry cache clear --all -v
poetry install
poetry run poe dev
```

### **Opción 3: Verificar Estado del Grafo**
```python
# Añadir logging en ai_whatsapp.py
print(f"🔄 Estado inicial: {state}")
print(f"🔄 Estado final: {result}")
```

---

## 🎯 **RESULTADO ESPERADO**

El flujo ahora debe:
1. ✅ **Detectar clientes existentes** y mostrar catálogo directamente
2. ✅ **Procesar servicios** sin bucles infinitos
3. ✅ **Agendar citas** y terminar correctamente
4. ✅ **Manejar errores** sin KeyError

**¡Listo para probar! El flujo debería funcionar exactamente como en la secuencia deseada.** 🎊
