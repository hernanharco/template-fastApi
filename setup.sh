#!/bin/bash

# Script de configuración para CoreAppointment Backend
# Reconoce automáticamente el entorno (development/production)
set -e  

# Colores para la terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Determinar el entorno (por defecto 'development')
ENVIRONMENT=${1:-development}
IMAGE_NAME="ima_backend-coreappointment"

echo -e "${BLUE}[STEP 1]${NC} 🚀 Iniciando en modo: ${CYAN}$ENVIRONMENT${NC}"

# 1. Gestión de dependencias con Poetry (Tus principios obligatorios)
if ! command -v poetry &> /dev/null; then
    echo -e "${YELLOW}[WARN]${NC} Poetry no encontrado. Instalando..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

echo -e "${GREEN}[INFO]${NC} Instalando dependencias..."
poetry install

# 2. Sincronización de Base de Datos (Neon)
# Corremos un pequeño script de python que cree las tablas si no existen
echo -e "${BLUE}[STEP 2]${NC} 🗄️ Sincronizando modelos con Neon..."
# Este comando asegura que ScheduledReminder y Appointment se creen antes de iniciar
poetry run python -c "from app.db.base import create_tables; create_tables()"

# 3. Gestión de Docker según entorno
if [ "$ENVIRONMENT" == "production" ]; then
    echo -e "${BLUE}[STEP 3]${NC} 📦 Construyendo imagen Docker para producción..."
    # Usamos --no-cache para asegurar que los cambios en los modelos se reflejen
    docker build -t $IMAGE_NAME:latest . 
    
    echo -e "${BLUE}[STEP 4]${NC} 🚢 Levantando contenedor..."
    # Limpia contenedores viejos
    docker rm -f $IMAGE_NAME-cont 2>/dev/null || true
    
    # Ejecuta el contenedor con políticas de reinicio
    docker run -d \
        --name $IMAGE_NAME-cont \
        --restart unless-stopped \
        -p 8000:8000 \
        --env-file .env \
        $IMAGE_NAME:latest
    
    echo -e "${GREEN}[SUCCESS]${NC} Backend producción activo en puerto 8000"
else
    echo -e "${YELLOW}[INFO]${NC} Modo desarrollo local activo."
    echo -e "${YELLOW}[INFO]${NC} Ejecuta: ${CYAN}poetry run uvicorn app.main:app --reload${NC}"
    echo -e "${YELLOW}[INFO]${NC} Para frontend usa pnpm dev en la otra carpeta."
fi

echo -e "${GREEN}[DONE]${NC} Configuración finalizada."