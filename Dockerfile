# Usa una base de Python estable (LTS) y un sistema operativo compatible (Debian)
FROM python:3.11-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instala dependencias del sistema operativo necesarias para compilar paquetes
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia solo el archivo de requerimientos para aprovechar la caché de Docker
COPY requirements.txt ./

# Instala TODAS las dependencias de Python desde el archivo de requerimientos
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo el código de tu aplicación al contenedor
COPY . .

# Expone el puerto que usará tu aplicación (ajústalo si es diferente)
EXPOSE 8002

# Comando para ejecutar la aplicación con Gunicorn (servidor de producción)
# Asegúrate de que 'wsgi:app' sea correcto para tu proyecto.
CMD ["gunicorn", "-c", "gunicorn_conf.py", "wsgi:app"]