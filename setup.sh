#!/bin/bash

# Script de configuración para CoreAppointment Backend
# Reconoce automáticamente el entorno (development/production) y configura todo lo necesario

set -e  # Detener el script si hay algún error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir mensajes con colores
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Detectar el entorno
ENVIRONMENT=${1:-development}

if [ "$ENVIRONMENT" != "development" ] && [ "$ENVIRONMENT" != "production" ]; then
    print_error "Entorno no válido. Usa 'development' o 'production'"
    echo "Uso: ./setup.sh [development|production]"
    exit 1
fi

print_message "🚀 Iniciando configuración para entorno: $ENVIRONMENT"

# Verificar si pnpm está instalado
if ! command -v pnpm &> /dev/null; then
    print_error "pnpm no está instalado. Por favor, instálalo primero:"
    echo "npm install -g pnpm"
    exit 1
fi

print_step "1/6 📁 Verificando estructura del proyecto..."

# Crear directorios necesarios si no existen
mkdir -p app/models app/schemas app/api/v1/endpoints app/core app/db

print_step "2/6 🐍 Configurando entorno Python..."

# Verificar si hay un entorno virtual
if [ ! -d "venv" ]; then
    print_message "Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
source venv/bin/activate

# Actualizar pip
print_message "Actualizando pip..."
pip install --upgrade pip

# Instalar dependencias de Python
print_message "Instalando dependencias de Python..."
pip install -r requirements.txt

print_step "3/6 🔧 Configurando variables de entorno..."

# Configurar archivo .env según el entorno
if [ "$ENVIRONMENT" = "production" ]; then
    if [ ! -f ".env" ]; then
        print_warning "Creando archivo .env para producción (debes configurar las variables manualmente)"
        cat > .env << EOF
# Configuración de Producción
ENVIRONMENT=production
DEBUG=false

# Base de Datos - Configura estas variables con tus datos reales
DATABASE_URL_PROD=postgresql://username:password@host:port/database_name

# Seguridad
SECRET_KEY=tu-super-secret-key-aqui

# CORS - Configura los dominios permitidos
CORS_ORIGINS_PROD=https://tudominio.com,https://www.tudominio.com

# API
API_V1_STR=/api/v1
EOF
        print_warning "⚠️  IMPORTANTE: Edita el archivo .env y configura las variables de producción"
    else
        print_message "Archivo .env ya existe para producción"
    fi
else
    if [ ! -f ".env" ]; then
        print_message "Creando archivo .env para desarrollo..."
        cat > .env << EOF
# Configuración de Desarrollo
ENVIRONMENT=development
DEBUG=true

# Base de Datos - Neon PostgreSQL (reemplaza con tus datos)
DATABASE_URL_DEV=postgresql://username:password@host:port/database_name

# Seguridad
SECRET_KEY=dev-secret-key-not-for-production

# CORS - Orígenes permitidos en desarrollo
CORS_ORIGINS_DEV=http://localhost:3000,http://127.0.0.1:3000

# API
API_V1_STR=/api/v1
EOF
        print_warning "⚠️  IMPORTANTE: Configura DATABASE_URL_DEV con tus datos de Neon PostgreSQL"
    else
        print_message "Archivo .env ya existe para desarrollo"
    fi
fi

print_step "4/6 🗄️ Verificando conexión a la base de datos..."

# Intentar verificar la conexión a la base de datos
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
    
    if [ ! -z "$DATABASE_URL_DEV" ] || [ ! -z "$DATABASE_URL_PROD" ]; then
        print_message "Variables de base de datos encontradas. Verificando conexión..."
        
        # Crear un script Python simple para verificar la conexión
        cat > check_db.py << 'EOF'
import os
import sys
sys.path.append('.')

try:
    from app.core.settings import settings
    from app.db.session import engine
    from sqlalchemy import text
    
    print("🔗 Probando conexión a la base de datos...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ Conexión exitosa a la base de datos")
except Exception as e:
    print(f"❌ Error de conexión: {e}")
    print("💡 Por favor, verifica tus credenciales en el archivo .env")
EOF

        python check_db.py
        rm check_db.py
    else
        print_warning "No se encontraron variables de base de datos configuradas"
    fi
fi

print_step "5/6 🏗️ Creando tablas en la base de datos..."

# Crear las tablas usando el script de la aplicación
python -c "
from app.db.session import create_tables
create_tables()
print('✅ Tablas creadas/verificadas exitosamente')
"

print_step "6/6 ✅ Verificando configuración final..."

# Verificar que todo esté en orden
if [ -f "app/main.py" ] && [ -f "requirements.txt" ] && [ -f ".env" ]; then
    print_message "🎉 Configuración completada exitosamente para entorno: $ENVIRONMENT"
    
    echo ""
    echo "📋 Resumen de la configuración:"
    echo "   • Entorno: $ENVIRONMENT"
    echo "   • Python: $(python --version)"
    echo "   • Estructura de directorios: ✅"
    echo "   • Dependencias Python: ✅"
    echo "   • Variables de entorno: ✅"
    echo "   • Base de datos: ✅"
    
    echo ""
    echo "🚀 Comandos útiles:"
    if [ "$ENVIRONMENT" = "development" ]; then
        echo "   • Iniciar servidor: pnpm dev"
        echo "   • Ver logs: tail -f logs/app.log"
        echo "   • Tests: pnpm test"
    else
        echo "   • Construir imagen: docker build -t coreappointment-api ."
        echo "   • Ejecutar con Docker: docker run -p 8000:8000 coreappointment-api"
    fi
    
    echo ""
    echo "📚 Documentación de la API:"
    echo "   • Swagger UI: http://localhost:8000/docs"
    echo "   • ReDoc: http://localhost:8000/redoc"
    
else
    print_error "❌ La configuración falló. Faltan archivos críticos."
    exit 1
fi

print_message "✨ ¡Listo para empezar a desarrollar!"
