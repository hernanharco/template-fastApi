🧭 Resumen del sistema hasta ahora
1️⃣ Entrada del sistema (Webhook)

El usuario escribe por WhatsApp.

Flujo:

Usuario
   ↓
WhatsApp Cloud API
   ↓
FastAPI webhook (/whatsapp)

Tu endpoint:

POST /whatsapp

Hace:

recibe mensaje

extrae phone

extrae text

muestra typing_on

envía el mensaje al agente

response_data = await maria_master.process_message(
    phone=user_phone,
    user_input=user_text
)

Luego envía la respuesta al usuario.

Arquitectura:

Webhook
   ↓
MariaMaster
   ↓
LangGraph Agent
2️⃣ MariaMaster (capa orquestadora)

Archivo:

app/agents/core/maria_master.py

Es el controlador principal del agente.

Responsabilidades:

• recibir mensajes del webhook
• preparar estado inicial
• ejecutar el graph
• devolver respuesta final

Flujo interno:

Webhook
   ↓
MariaMaster.process_message()
   ↓
LangGraph Graph.invoke()
   ↓
State actualizado
   ↓
Respuesta final
3️⃣ State del agente

Archivo:

app/agents/router/state.py

Define la memoria del agente.

class RoutingState(TypedDict):

Contiene:

Conversación
messages

Historial del chat.

Catálogo
shown_service_ids
selected_service_id

Evita repetir servicios mostrados.

Inteligencia temporal
selected_date
time_filter
selection_preference

Ejemplo:

mañana por la tarde

Se traduce a:

selected_date = 2026-03-07
time_filter = 15:00
Booking
active_slots
booking_for_name
other_day_attempts

Permite manejar disponibilidad y reintentos.

Cliente
client_phone
client_name
is_new_user
Control del flujo
intent
next_action

Esto es lo que usa el router.

4️⃣ Graph del agente

Archivo:

app/agents/graph.py

El cerebro del flujo conversacional.

Creación:

workflow = StateGraph(RoutingState)
Nodos registrados
customer_lookup
router
greeting
catalog
booking
appointments

Cada nodo es una habilidad del agente.

5️⃣ Flujo del graph
Inicio
START
 ↓
customer_lookup
 ↓
router
Router decide
intent

Posibles rutas:

GREETING
CATALOG
BOOKING
CONFIRMATION
FINISH
Flujo visual
            ┌──────── greeting
START
   ↓
customer_lookup
   ↓
router ──────── catalog
   │              │
   │              │
   │              ↓
   │            booking
   │              │
   │              ↓
   └───────── appointments
6️⃣ Nodos del agente

Cada nodo está en:

app/agents/<domain>/nodes.py

Ejemplo:

agents/
   greeting/
   catalog/
   booking/
   appointments/

Responsabilidad de un nodo:

leer state
↓
hacer lógica
↓
usar tools
↓
actualizar state

Nunca deben hacer lógica pesada.

7️⃣ Tools del agente

Ubicación:

app/agents/tools/

Las tools son adaptadores del agente a los servicios reales.

Ejemplo:

get_booking_options_tool.py
confirm_booking_tool.py

Flujo:

Node
 ↓
Tool
 ↓
Service
 ↓
DB
8️⃣ Services (lógica de negocio)

Ubicación:

app/services/

Aquí vive la lógica real del negocio.

Ejemplo:

availability.py
booking_scheduler.py
appointment_manager.py

Tu sistema de booking hace:

1️⃣ Buscar slots
get_available_slots()
2️⃣ Priorizar favoritos
preferred_collaborator_ids
3️⃣ Generar 2 opciones

Ejemplo:

10:30 con Ana ⭐
11:00 con Pedro
4️⃣ Confirmar cita
confirm_booking_option()

Esto:

• valida fecha
• calcula duración
• crea cita
• genera enlace Telegram
9️⃣ Models

Ejemplo:

Service
Client
Collaborator
Appointment

El agente no toca directamente los models.

Siempre pasa por:

services
🔟 Flujo completo del sistema

El viaje de un mensaje:

Usuario: "quiero cortarme el pelo"

WhatsApp
   ↓
Webhook
   ↓
MariaMaster
   ↓
LangGraph Graph
   ↓
Router Node
   ↓
Catalog Node
   ↓
Tool
   ↓
Service
   ↓
DB
   ↓
Respuesta
   ↓
WhatsApp
📦 Arquitectura final hasta ahora
app/

agents/
   core/
      maria_master.py

   router/
      state.py

   nodes/
      router_node.py
      greeting_node.py
      catalog_node.py
      booking_node.py
      confirmation_node.py

   tools/
      get_booking_options_tool.py
      confirm_booking_tool.py

   graph.py


services/
   availability.py
   booking_scheduler.py
   appointment_manager.py


models/
   service.py
   client.py
   appointment.py
   collaborator.py


api/
   whatsapp_webhook.py
🧠 Estado del proyecto ahora

Tu sistema ya tiene:

✅ backend serio
✅ separación de dominios
✅ LangGraph agent
✅ memoria conversacional
✅ booking inteligente
✅ favoritos de cliente
✅ confirmación automática

Eso ya está muy por encima del 90% de bots de WhatsApp.

🚀 Lo siguiente que haría (muy importante)

Antes de seguir construyendo más cosas, falta una pieza crítica para agentes en producción:

Memory persistence

Para que el agente recuerde conversaciones entre mensajes.

Con algo como:

Redis
o
Postgres memory store

Esto hace que el agente sea 10x más natural.

Si quieres, en el siguiente paso te enseño algo que cambia completamente la estabilidad del agente:

👉 Cómo agregar Session Memory + Conversation Threads, que es lo que usan los agentes reales en producción.