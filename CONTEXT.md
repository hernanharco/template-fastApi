# CoreAppointment Backend - Contexto Técnico Completo

## 📋 Resumen del Proyecto

**CoreAppointment** es un backend SaaS modular de agendamiento construido con FastAPI, LangGraph y Neon PostgreSQL. Implementa un sistema de agentes conversacionales IA para gestionar reservas de servicios de manera automatizada.

## 🏗️ Arquitectura General

### Stack Tecnológico
- **Backend**: FastAPI + Python 3.12+
- **Base de Datos**: Neon PostgreSQL (serverless)
- **Agentes IA**: LangGraph con LangChain
- **ORM**: SQLAlchemy 2.0+
- **Validación**: Pydantic v2
- **Container**: Docker multi-stage
- **Package Manager**: Poetry

### Estructura de Directorios
```
Backend-CoreAppointment/
├── app/
│   ├── agents/           # Sistema de agentes LangGraph
│   │   ├── core/         # Lógica central de agentes
│   │   ├── nodes/        # Nodos del grafo de conversación
│   │   ├── routing/      # Enrutamiento y estado
│   │   ├── schemas/      # Modelos Pydantic de agentes
│   │   ├── tools/        # Tools de LangChain
│   │   ├── memory/       # Sistema de memoria conversacional
│   │   └── formatters/   # Formateo de respuestas
│   ├── api/              # Endpoints REST API
│   ├── models/           # Modelos SQLAlchemy
│   ├── services/         # Lógica de negocio
│   ├── schemas/          # Schemas Pydantic API
│   ├── core/             # Configuración y settings
│   ├── db/               # Sesiones de base de datos
│   └── main.py           # Aplicación FastAPI principal
├── tests/                # Suite de tests
├── migrations/           # Migraciones Alembic
└── scripts/              # Scripts de utilidad
```

## 🤖 Sistema de Agentes LangGraph

### Grafo Principal de Conversación
El flujo está definido en `app/agents/routing/graph.py`:

```python
START → customer_lookup → router → {
    GREETING → greeting → {WAIT, CATALOG}
    CATALOG → catalog → {BOOKING, FINISH}
    BOOKING → booking → {CONFIRMATION, CATALOG, FINISH}
    CONFIRMATION → END
}
```

### Nodos del Sistema

### Nodos del Sistema

1. **booking_node**: Nodo de booking
2. **catalog_node**: 
    Nodo responsable de:
    1. Mostrar catálogo cuando aún no hay servicio elegido
    2. Resolver el texto del usuario a un servicio real
    3. Pasar a BOOKING cuando el usuario ya eligió servicio
    
3. **confirmation_node**: Nodo de confirmation
4. **customer_lookup_node**: 
    Busca o crea al cliente en base de datos usando su teléfono.
    Si el cliente aún tiene el nombre por defecto, marca wait_for_name=True
    para que el flujo de greeting solicite su nombre.
    
5. **finish_node**: 
    Nodo ejecutado tras confirmar una cita exitosamente.
    Responsabilidades (SRP):
      - Adjuntar pregunta de seguimiento al mensaje de confirmación.
      - Limpiar el estado de la conversación para un nuevo ciclo.
      - Marcar intent como CATALOG para que el router sepa que
        el próximo mensaje del usuario debe ir al catálogo.
    
6. **greeting_node**: Nodo de greeting
7. **router_node**: Nodo de router
8. **time_filter_node**: Nodo de time_filter
9. **time_parser_node**: 
    Solo se activa cuando el usuario ya vio slots y pide otro día.
    Si no hay active_slots previos, pasa directo sin hacer nada.
    


## 📊 Modelos de Datos SQLAlchemy

### Entidades Principales

### Entidades Principales

#### Appointment
```python
class Appointment(Base):
    id: ...
    client_id: ...
    service_id: ...
    collaborator_id: ...
    client_name: ...
    client_phone: ...
    client_email: ...
    client_notes: ...
    source: ...
    start_time: ...
    end_time: ...
    status: ...
    created_at: ...
    updated_at: ...

    # Relaciones
    client: ...
    service: ...
    collaborator: ...
    reminders: ...
```

#### AIAuditLog
```python
class AIAuditLog(Base):
    id: ...
    phone_number: ...
    user_message: ...
    detected_intent: ...
    detected_service: ...
    final_response: ...
    state_before: ...
    state_after: ...
    created_at: ...
```

#### BusinessHours
```python
class BusinessHours(Base):
    id: ...
    day_of_week: ...
    day_name: ...
    is_enabled: ...
    is_split_shift: ...
    collaborator_id: ...
    created_at: ...
    updated_at: ...

    # Relaciones
    time_slots: ...
    collaborator: ...
```

#### TimeSlot
```python
class TimeSlot(Base):
    id: ...
    start_time: ...
    end_time: ...
    slot_order: ...
    business_hours_id: ...
    created_at: ...
    updated_at: ...

    # Relaciones
    business_hours: ...
```

#### Client
```python
class Client(Base):
    id: ...
    business_id: ...
    full_name: ...
    phone: ...
    email: ...
    notes: ...
    is_active: ...
    current_service_id: ...
    current_collaborator_id: ...
    source: ...
    metadata_json: ...
    created_at: ...
    updated_at: ...

    # Relaciones
    appointments: ...
    current_collaborator: ...
```

#### Collaborator
```python
class Collaborator(Base):
    id: ...
    name: ...
    email: ...
    is_active: ...
    created_at: ...

    # Relaciones
    departments: ...
    business_hours: ...
    appointments: ...
```

#### Department
```python
class Department(Base):
    id: ...
    name: ...
    description: ...
    color: ...
    is_active: ...
    created_at: ...

    # Relaciones
    services: ...
    collaborators: ...
```

#### AiLearningLog
```python
class AiLearningLog(Base):
    id: ...
    created_at: ...
    phone: ...
    module_name: ...
    user_message: ...
    ai_response: ...
    is_resolved: ...
    notes: ...
```

#### ApiRouteMetric
```python
class ApiRouteMetric(Base):
    id: ...
    path: ...
    method: ...
    status_code: ...
    process_time: ...
    created_at: ...
```

#### ScheduledReminder
```python
class ScheduledReminder(Base):
    id: ...
    appointment_id: ...
    phone: ...
    telegram_chat_id: ...
    message: ...
    scheduled_for: ...
    sent: ...
    prefer_channel: ...

    # Relaciones
    appointment: ...
```

#### Service
```python
class Service(Base):
    id: ...
    name: ...
    duration_minutes: ...
    price: ...
    is_active: ...
    department_id: ...
    created_at: ...
    updated_at: ...

    # Relaciones
    department: ...
    appointments: ...
```


## 🔧 Modelos Pydantic

### Schemas de Agentes

### Schemas de Agentes

- **ServiceReadSimple** (appointments)
- **AppointmentBase** (appointments)
- **DepartmentReadSimple** (appointments)
- **AppointmentRead** (appointments)
- **AppointmentUpdate** (appointments)
- **TimeSlot** (appointments)
- **AvailableSlotsResponse** (appointments)
- **DayCountResponse** (appointments)
- **TimeSlotBase** (business_hours)
- **BusinessHoursBase** (business_hours)
- **BusinessHoursUpdate** (business_hours)
- **TimeSlotUpdate** (business_hours)
- **BulkBusinessHoursUpdate** (business_hours)
- **ClientBase** (client)
- **ClientUpdate** (client)
- **CollaboratorBase** (collaborators)
- **CollaboratorUpdate** (collaborators)
- **DepartmentBase** (department)
- **DepartmentUpdate** (department)
- **ReminderBase** (reminder)
- **ServiceBase** (services)
- **ServiceUpdate** (services)
- **AppointmentData** (appointments)
- **AppointmentConfirmationOutput** (appointments)
- **BookingOption** (booking)
- **BookingOptionsResponse** (booking)
- **SlotValidationResponse** (booking)
- **CatalogServiceItem** (catalog)
- **CatalogInput** (catalog)
- **CatalogOutput** (catalog)
- **ClientLookupResponse** (client)
- **GreetingInput** (greeting)
- **GreetingOutput** (greeting)


## 🚀 Estado Actual del Sistema

### ✅ Funcionalidades Implementadas
1. **Sistema Completo de Agentes**: LangGraph con 6 nodos funcionales
2. **Gestión de Clientes**: Registro, búsqueda y persistencia
3. **Catálogo de Servicios**: Listado y selección con fuzzy matching
4. **Disponibilidad en Tiempo Real**: Búsqueda de slots por colaborador
5. **Reservas Automatizadas**: Flujo completo de booking
6. **Memoria Conversacional**: Contexto persistente por teléfono
7. **Manejo de Horarios Partidos**: Soporte para múltiples turnos por día
8. **Validaciones Robustas**: Detección de fechas relativas ("mañana", "lunes")
9. **API REST Endpoints**: CRUD completo para todas las entidades
10. **Docker Multi-stage**: Imágenes optimizadas para producción

### 🧪 Calidad del Código
- **Tests Automatizados**: 25 tests pasando (100% success rate)
- **Cobertura de Flujo**: Tests para routing, booking, fuzzy matching
- **Manejo de Errores**: Sistema robusto de validación y rollback
- **Logging Descriptivo**: Trazabilidad completa del flujo de agentes

## 🚧 Funcionalidades Pendientes por Implementar

### 🔥 Alta Prioridad
1. **Sistema de Recordatorios**
   - Modelo ScheduledReminder (definido pero no implementado)
   - Envío automático de SMS/Email antes de citas
   - Configuración de tiempos de recordatorio

2. **Gestión de Colaboradores**
   - CRUD completo de colaboradores
   - Asignación de servicios por colaborador
   - Gestión de disponibilidad individual

3. **Panel de Administración Web**
   - Dashboard para gestión de citas
   - Vista de calendario semanal/mensual
   - Gestión de clientes y servicios

4. **Sistema de Pagos**
   - Integración con pasarelas de pago
   - Gestión de depósitos para reservas
   - Reembolsos automáticos

### 📈 Media Prioridad
5. **Notificaciones Push/WebSockets**
   - Actualizaciones en tiempo real del calendario
   - Notificaciones de nuevas reservas

6. **Reportes y Analíticas**
   - Métricas de ocupación
   - Reportes financieros
   - Análisis de demanda por servicio

7. **Sistema de Calificaciones**
   - Calificación de servicios y colaboradores
   - Feedback automático post-cita

8. **Gestión de Cancelaciones**
   - Políticas de cancelación
   - Reagendamiento automático
   - Penalizaciones por no-show

### 🔮 Baja Prioridad / Futuro
9. **Multi-tenant Completo**
   - Aislamiento de datos por negocio
   - Configuración personalizada por tenant

10. **Integraciones Externas**
    - Sincronización con Google Calendar
    - Integración con WhatsApp Business
    - Conexión con sistemas de gestión existentes

11. **IA Avanzada**
    - Predicción de demanda
    - Optimización automática de horarios
    - Chatbot con contexto histórico más profundo

## 🔄 Flujo de Usuario Actual

### Conversación Típica
```
Usuario: "Hola"
Maria: "¡Hola! Soy Maria, tu asistente virtual. ¿Cuál es tu nombre?"

Usuario: "Juan Pérez"
Maria: "Mucho gusto Juan. Te mostraré nuestros servicios: [lista]"

Usuario: "Quiero cortarme el cabello"
Maria: "Perfecto. Para cuándo te gustaría agendar?"

Usuario: "Mañana a las 3pm"
Maria: "Tengo disponibilidad mañana a las 3:00pm con [colaborador]. Confirmo?"

Usuario: "Sí"
Maria: "✅ Reserva confirmada. Te enviaré un recordatorio."
```

## 🛠️ Configuración y Despliegue

### Variables de Entorno Clave
```env
ENVIRONMENT=development|production
DATABASE_URL_DEV=postgresql://...
DATABASE_URL_PROD=postgresql://...
OPENAI_API_KEY=sk-...
LANGSMITH_TRACING=true
```

### Comandos Útiles (Poetry)
```bash
poetry run poe dev          # Servidor desarrollo
poetry run poe test         # Ejecutar tests
poetry run poe db-plan "msg" # Crear migración
poetry run poe db-migrate   # Aplicar migraciones
```

### Endpoints API Principales
- `GET /docs` - Documentación Swagger
- `POST /chat` - Interacción con agentes
- `GET /services` - Listar servicios
- `POST /appointments` - Crear cita
- `GET /health` - Health check

## 📝 Notas Técnicas Importantes

1. **Estado Volátil**: Los campos `current_*` en Client son para la sesión actual
2. **JSONB en Neon**: `metadata_json` permite consultas rápidas sobre preferencias
3. **LangGraph Checkpoints**: Estado persistente del grafo en PostgreSQL
4. **Fuzzy Matching**: Sistema de matching de servicios con thefuzz
5. **Manejo de Timezones**: Todos los datetime usan timezone-aware
6. **Rollbacks Automáticos**: Cada transacción tiene proper error handling

---

*Este documento refleja el estado actual del proyecto al 9 de marzo de 2026.*
