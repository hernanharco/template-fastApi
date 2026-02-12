# ETAPA 1: Constructor (Builder) [cite: 2026-02-07]
FROM python:3.12-alpine AS builder

WORKDIR /app

# Instalamos dependencias necesarias para compilar librerías de PostgreSQL
RUN apk add --no-cache gcc musl-dev postgresql-dev libffi-dev

COPY requirements.txt .
# Instalamos las librerías en una carpeta temporal
RUN pip install --user --no-cache-dir -r requirements.txt

# ETAPA 2: Ejecución (Runtime) [cite: 2026-02-07]
FROM python:3.12-alpine AS runtime

WORKDIR /app

# Instalamos solo la librería mínima para que PostgreSQL funcione
RUN apk add --no-cache libpq

# Copiamos las librerías instaladas desde la etapa anterior [cite: 2026-01-30]
COPY --from=builder /root/.local /root/.local
COPY . .

# Aseguramos que Python encuentre las librerías
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Exponemos el puerto de FastAPI [cite: 2026-02-07]
EXPOSE 8000

# Comando para arrancar la aplicación
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]