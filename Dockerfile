<<<<<<< HEAD
# Dockerfile optimizado para FastAPI con Python 3.12
# Basado en Alpine Linux para reducir el tamaño de la imagen

# Etapa 1: Builder - Instalación de dependencias
FROM python:3.12-alpine AS builder

# Establecemos el directorio de trabajo
WORKDIR /app

# Instalamos dependencias del sistema necesarias para psycopg2
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    libffi-dev \
    python3-dev

# Copiamos solo los archivos de dependencias primero
COPY requirements.txt .

# Instalamos las dependencias de Python en modo optimizado
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Etapa 2: Runtime - Imagen final limpia
FROM python:3.12-alpine AS runtime

# Creamos un usuario no root para seguridad
RUN addgroup -g 1000 fastapi && \
    adduser -D -s /bin/sh -u 1000 -G fastapi fastapi

# Instalamos solo las dependencias runtime necesarias
RUN apk add --no-cache \
    libpq \
    && rm -rf /var/cache/apk/*

# Establecemos el directorio de trabajo
WORKDIR /app

# Copiamos las dependencias instaladas desde la etapa builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiamos el código de la aplicación
COPY . .

# Cambiamos al usuario no root
USER fastapi

# Exponemos el puerto de la aplicación
EXPOSE 8000

# Variables de entorno por defecto
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Comando para ejecutar la aplicación
# Usamos uvicorn con configuración optimizada para producción
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
=======
# 1. Imagen base de Python liviana
FROM python:3.12-slim

# 2. Evitar que Python genere archivos basura (.pyc) y ver logs rápido
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# 3. Instalamos lsof (necesario para tu setup.sh)
RUN apt-get update && apt-get install -y lsof && rm -rf /var/lib/apt/lists/*

# 4. Copiamos requerimientos e instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiamos el código y el script
COPY . .

# 6. Damos permisos de ejecución al script
RUN chmod +x setup.sh

# 7. Exponemos el puerto
EXPOSE 8000

# 8. El contenedor arranca usando tu lógica de setup.sh
# Por defecto lo lanzamos en producción
ENTRYPOINT ["/bin/bash", "setup.sh"]
CMD ["production"]
>>>>>>> 527e4de9f5b4a6feec2737105b4ebde55f7fdcd9
