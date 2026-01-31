# Backend FastAPI Application

Backend API construido con FastAPI y Neon PostgreSQL que detecta automáticamente el entorno (desarrollo/producción) y ajusta su configuración dinámicamente.

## 🚀 Características Principales

- **FastAPI Framework**: API moderna y asíncrona con documentación automática
- **Neon PostgreSQL**: Base de datos serverless PostgreSQL en la nube
- **Detección Automática de Entorno**: Configuración separada para desarrollo y producción
- **CORS Dinámico**: Orígenes permitidos según el entorno
- **Gestión de Ciclo de Vida**: Startup y shutdown handlers para recursos
- **Health Checks**: Endpoints para verificar estado de la aplicación y conexión a DB
- **Manejo Robusto de Errores**: Captura de fallos de conexión sin detener el servidor

## 📁 Estructura del Proyecto

```
backend/
├── app/
│   ├── __init__.py
│   ├── core/
│   │   └── settings.py      # Configuración y detección de entorno
│   ├── db/
│   │   └── session.py       # Conexión a base de datos Neon
│   └── main.py              # Aplicación FastAPI principal
├── .env                     # Variables de entorno (no versionar)
├── .env.example             # Plantilla de configuración
├── requirements.txt         # Dependencias Python
└── README.md               # Este archivo
```

## 🛠️ Configuración del Entorno

### 1. Crear Entorno Virtual

# Environment Configuration

#### Linux/macOS
```bash
# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
source venv/bin/activate
```

#### Windows
```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
venv\Scripts\activate
```

### 2. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar Variables de Entorno

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar el archivo .env con tu configuración
nano .env  # o tu editor preferido
```

**Variables importantes a configurar:**

```env
# Entorno (development/production)
ENVIRONMENT=development

# Base de datos Neon - Configura tus URLs reales
DATABASE_URL_DEV=postgresql://usuario:password@ep-xxx.us-east-2.aws.neon.tech/dbname?sslmode=require
DATABASE_URL_PROD=postgresql://usuario:password@ep-xxx.us-east-2.aws.neon.tech/dbname?sslmode=require

# Configuración CORS
CORS_ORIGINS_DEV=http://localhost:3000,http://127.0.0.1:3000
CORS_ORIGINS_PROD=https://tu-saas-real.com,https://admin.tu-saas.com

# Seguridad
SECRET_KEY=your-secret-key-change-in-production
DEBUG=true
```

## 🗄️ Configuración de Base de Datos Neon

1. **Crear cuenta en Neon**: Visita [neon.tech](https://neon.tech)
2. **Crear nuevo proyecto**: Selecciona PostgreSQL
3. **Copiar connection string**: Obtén la URL de conexión
4. **Configurar en .env**: Pega la URL en `DATABASE_URL_DEV` o `DATABASE_URL_PROD`

## 🚀 Ejecutar la Aplicación

### Modo Desarrollo (con auto-reload)

```bash
python -m app.main
```

### O usando Uvicorn directamente

```bash
# Desarrollo
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Producción
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Verificar que está funcionando

Abre tu navegador y visita:
- **API Principal**: http://localhost:8000
- **Documentación Swagger**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Info App**: http://localhost:8000/info

## 📡 Endpoints de la API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Información básica de la API |
| GET | `/health` | Verifica conexión a la base de datos |
| GET | `/info` | Información detallada del entorno |
| GET | `/docs` | Documentación interactiva Swagger |

## 🔧 Detección Automática de Entorno

La aplicación detecta automáticamente el entorno basado en la variable `ENVIRONMENT`:

### Desarrollo (`ENVIRONMENT=development`)
- Usa `DATABASE_URL_DEV` para la base de datos
- CORS permite orígenes locales (`localhost:3000`, `127.0.0.1:3000`)
- Auto-reload activado
- Debug mode habilitado
- Logs verbosos

### Producción (`ENVIRONMENT=production`)
- Usa `DATABASE_URL_PROD` para la base de datos
- CORS restringido a dominios específicos
- Auto-reload desactivado
- Debug mode desactivado
- Logs optimizados

## 🛡️ Manejo de Errores

La aplicación incluye manejo robusto de errores:

- **Conexión a DB**: Si la URL es incorrecta, muestra advertencia sin detener el servidor
- **Validación de Config**: Verifica que todas las variables requeridas estén presentes
- **Health Checks**: Endpoints para monitorear estado del sistema

## 📦 Dependencias Principales

- `fastapi`: Framework web moderno
- `uvicorn`: Servidor ASGI
- `sqlalchemy`: ORM para base de datos
- `psycopg2-binary`: Driver PostgreSQL
- `pydantic-settings`: Configuración con validación
- `python-dotenv`: Manejo de variables de entorno

## 🔄 Flujo de Trabajo Típico

1. **Clonar el repositorio**
2. **Crear y activar entorno virtual**
3. **Instalar dependencias**
4. **Configurar .env con credenciales de Neon**
5. **Ejecutar la aplicación**
6. **Probar endpoints en http://localhost:8000/docs**

## 🐛 Solución de Problemas Comunes

### Error de conexión a la base de datos
```bash
⚠️  AVISO DE CONFIGURACIÓN DE BASE DE DATOS
No se pudo conectar a la base de datos en: development
```
**Solución**: Verifica que la URL en `.env` sea correcta y que las credenciales de Neon sean válidas.

### Error de importación
```bash
ModuleNotFoundError: No module named 'app'
```
**Solución**: Asegúrate de estar en el directorio raíz del proyecto y que el entorno virtual esté activado.

### Puerto en uso
```bash
Address already in use
```
**Solución**: Cambia el puerto o detén el proceso que está usando el puerto 8000.

## 📝 Notas Adicionales

- El archivo `.env` contiene información sensible y no debe ser versionado
- En producción, usa variables de entorno del sistema en lugar del archivo `.env`
- La aplicación maneja gracefully los shutdowns, cerrando conexiones a la base de datos
- Los logs están configurados para mostrar información relevante según el entorno