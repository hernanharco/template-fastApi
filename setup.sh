#!/bin/bash

# --- Colores e Iconos ---
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'
DOCKER="🐳"

# 1. Cargar variables desde el .env
if [ -f .env ]; then
    TITLE_BACKEND=$(grep TITLE_BACKEND .env | cut -d '=' -f2)
else
    # Si no hay .env pero estamos en Docker, TITLE_BACKEND vendrá por ENV
    TITLE_BACKEND=${TITLE_BACKEND:-"SaaS-Backend"}
fi

# 2. Preparar nombres en minúsculas
TITLE_LOWERCASE=${TITLE_BACKEND,,}
IMAGE_NAME="ima_${TITLE_LOWERCASE}"
CONTAINER_NAME="cont_${TITLE_LOWERCASE}"

MODE=${1:-development}
PORT=8000

# 3. DETECTAR SI ESTAMOS DENTRO DE DOCKER
# Los contenedores suelen tener el archivo /.dockerenv
INSIDE_DOCKER=false
if [ -f /.dockerenv ]; then
    INSIDE_DOCKER=true
fi

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}    PROYECTO: ${TITLE_BACKEND}           ${NC}"
echo -e "${BLUE}=========================================${NC}"

if [ "$INSIDE_DOCKER" = true ]; then
    # --- LÓGICA DENTRO DEL CONTENEDOR ---
    echo -e "${GREEN}${DOCKER} Iniciando Servidor en Producción (Interno)...${NC}"
    # Aquí ya no usamos el venv porque la imagen de Docker ya es el entorno
    python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
    
elif [ "$MODE" == "production" ]; then
    # --- LÓGICA EN TU PC (HOST) ---
    echo -e "${GREEN}${DOCKER} Preparando Contenedor: ${CONTAINER_NAME}${NC}"
    
    docker build -t ${IMAGE_NAME}:latest .
    docker stop ${CONTAINER_NAME} 2>/dev/null
    docker rm ${CONTAINER_NAME} 2>/dev/null
    
    docker run -d \
        --name ${CONTAINER_NAME} \
        -p ${PORT}:8000 \
        --env-file .env \
        ${IMAGE_NAME}:latest
    
    echo -e "${GREEN}✅ ¡Contenedor creado! Logs disponibles en VS Code.${NC}"

else
    # --- LÓGICA DESARROLLO LOCAL ---
    echo -e "${BLUE}🛠️ Iniciando Desarrollo Local...${NC}"
    fuser -k -9 ${PORT}/tcp 2>/dev/null
    ./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --reload
fi