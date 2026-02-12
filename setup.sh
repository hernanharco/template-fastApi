#!/bin/bash

# Script de configuración para CoreAppointment Backend
# Reconoce automáticamente el entorno (development/production)
set -e  # Detener el script si hay algún error

# Colores para la terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Determinar el entorno (por defecto 'development')
ENVIRONMENT=${1:-development}
IMAGE_NAME="ima_backend-coreappointment"

echo -e "${BLUE}[STEP 1]${NC} 🚀 Iniciando en modo: $ENVIRONMENT"

# 1. Configuración del Entorno Virtual (Siempre útil para el editor)
if [ ! -d "venv" ]; then
    echo -e "${GREEN}[INFO]${NC} Creando entorno virtual..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 2. Gestión de Docker según entorno
if [ "$ENVIRONMENT" == "production" ]; then
    echo -e "${BLUE}[STEP 2]${NC} 📦 Construyendo imagen Docker..."
    # Construye la imagen que verás en VS Code
    docker build -t $IMAGE_NAME:latest . 
    
    echo -e "${BLUE}[STEP 3]${NC} 🚢 Levantando contenedor..."
    # Limpia contenedores viejos con el mismo nombre
    docker rm -f $IMAGE_NAME-cont 2>/dev/null || true
    
    # Ejecuta el contenedor (Aparecerá en el panel 'Containers')
    docker run -d \
        --name $IMAGE_NAME-cont \
        -p 8000:8000 \
        --env-file .env \
        $IMAGE_NAME:latest
    
    echo -e "${GREEN}[SUCCESS]${NC} Contenedor activo en puerto 8000"
else
    echo -e "${YELLOW}[INFO]${NC} Modo desarrollo: Usa 'source venv/bin/activate' y 'pnpm dev'"
    echo -e "${YELLOW}[INFO]${NC} Para ver el contenedor en VS Code, usa: ./setup.sh production"
fi

echo -e "${GREEN}[DONE]${NC} Configuración finalizada."