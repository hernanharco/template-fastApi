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