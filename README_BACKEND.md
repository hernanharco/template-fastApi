# CoreAppointment Backend - API de Servicios y Horarios

Backend FastAPI con arquitectura modular para la gestión de servicios y horarios de negocio.

## 🏗️ Arquitectura

El proyecto sigue una arquitectura modular con dos dominios principales:

### 📦 Dominio: Services
Gestión del catálogo de servicios (nombre, duración, precio).

- **Modelo**: `app/models/services.py` - Entidad Service con SQLAlchemy
- **Esquemas**: `app/schemas/services.py` - Pydantic schemas (Create, Read, Update)
- **Endpoints**: `app/api/v1/endpoints/services.py` - CRUD completo

### 📦 Dominio: Business Hours
Gestión de horarios con soporte para turnos partidos y múltiples rangos de tiempo.

- **Modelos**: `app/models/business_hours.py` - Entidades BusinessHours y TimeSlot
- **Esquemas**: `app/schemas/business_hours.py` - Validación compleja de horarios
- **Endpoints**: `app/api/v1/endpoints/business_hours.py` - Gestión completa de horarios

## 🚀 Configuración Rápida

### Requisitos Previos
- Python 3.12+
- PostgreSQL (Neon recomendado)
- pnpm (para gestión de scripts)

### Instalación Automática

```bash
# Para entorno de desarrollo
./setup.sh development

# Para entorno de producción
./setup.sh production
```

El script `setup.sh` detecta automáticamente el entorno y configura:
- Entorno virtual Python
- Dependencias del proyecto
- Variables de entorno
- Estructura de base de datos
- Verificación de conexión

### Configuración Manual

1. **Clonar y configurar entorno**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env con tus credenciales de Neon PostgreSQL
```

3. **Crear tablas**
```bash
pnpm db:migrate
```

## 📡 Endpoints de la API

### Services (`/api/v1/services`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/` | Crear nuevo servicio |
| GET | `/` | Listar servicios (con filtros) |
| GET | `/{id}` | Obtener servicio específico |
| PUT | `/{id}` | Actualizar servicio |
| DELETE | `/{id}` | Eliminar servicio (soft delete) |
| GET | `/stats/summary` | Estadísticas de servicios |

### Business Hours (`/api/v1/business-hours`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/` | Crear configuración de horarios |
| GET | `/` | Listar todas las configuraciones |
| GET | `/{id}` | Obtener configuración específica |
| GET | `/day/{day_name}` | Obtener horario por día |
| PUT | `/{id}` | Actualizar configuración |
| DELETE | `/{id}` | Eliminar configuración |
| POST | `/initialize-week` | Inicializar semana completa |

## 🐳 Docker

### Construir imagen
```bash
pnpm docker:build
```

### Ejecutar con Docker
```bash
pnpm docker:run
```

El Dockerfile está optimizado con:
- Multi-stage build para reducir tamaño
- Usuario no root para seguridad
- Alpine Linux base
- Configuración de producción lista

## 📝 Scripts Disponibles (pnpm)

```bash
# Desarrollo
pnpm dev              # Iniciar servidor en modo desarrollo
pnpm dev:reload       # Iniciar con auto-reload

# Producción
pnpm start            # Iniciar servidor en producción

# Configuración
pnpm setup:dev        # Configurar entorno desarrollo
pnpm setup:prod       # Configurar entorno producción

# Base de Datos
pnpm db:migrate       # Crear tablas
pnpm db:reset         # Resetear base de datos

# Calidad de Código
pnpm lint             # Verificar estilo de código
pnpm format           # Formatear código
pnpm test             # Ejecutar tests
```

## 🏛️ Estructura del Proyecto

```
Backend-CoreAppointment/
├── app/
│   ├── api/v1/
│   │   ├── endpoints/
│   │   │   ├── services.py      # Endpoints de servicios
│   │   │   └── business_hours.py # Endpoints de horarios
│   │   └── api.py               # Router principal
│   ├── core/
│   │   └── settings.py          # Configuración centralizada
│   ├── db/
│   │   └── session.py           # Conexión a base de datos
│   ├── models/
│   │   ├── base.py              # Modelo base SQLAlchemy
│   │   ├── services.py          # Modelo Service
│   │   └── business_hours.py    # Modelos BusinessHours y TimeSlot
│   ├── schemas/
│   │   ├── services.py          # Schemas Pydantic para servicios
│   │   └── business_hours.py    # Schemas Pydantic para horarios
│   └── main.py                  # Aplicación FastAPI principal
├── Dockerfile                   # Configuración Docker optimizada
├── setup.sh                     # Script de configuración automática
├── package.json                 # Scripts pnpm
└── requirements.txt             # Dependencias Python
```

## 🔧 Características Técnicas

### Modelos de Datos
- **Service**: Catálogo de servicios con validaciones de negocio
- **BusinessHours**: Configuración por día con soporte para turnos partidos
- **TimeSlot**: Rangos de tiempo individuales con ordenamiento

### Validaciones
- Nombres de servicios únicos
- Duraciones en múltiplos de 5 minutos
- Precios con 2 decimales máximo
- Horarios con validación de rangos lógicos
- Turnos partidos con exactamente 2 slots

### Seguridad
- Soft delete para servicios
- Usuario no root en Docker
- Variables de entorno separadas por entorno
- CORS configurado dinámicamente

### Documentación
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Endpoints de health check

## 🌐 Entornos

### Development
- Auto-reload activado
- Debug mode
- Logs detallados
- CORS para localhost

### Production
- Workers optimizados
- Seguridad reforzada
- Logs minimizados
- CORS configurado para dominios específicos

## 📊 Flujo de Datos

1. **Frontend** → API Request → **FastAPI Router**
2. **Router** → Pydantic Validation → **Service Layer**
3. **Service Layer** → SQLAlchemy ORM → **PostgreSQL**
4. **Response** ← Pydantic Serialization ← **Database Results**

## 🤝 Contribución

1. Fork del proyecto
2. Crear feature branch: `git checkout -b feature/nueva-funcionalidad`
3. Commit changes: `git commit -am 'Agregar nueva funcionalidad'`
4. Push to branch: `git push origin feature/nueva-funcionalidad`
5. Submit Pull Request

## 📄 Licencia

MIT License - ver archivo LICENSE para detalles.
