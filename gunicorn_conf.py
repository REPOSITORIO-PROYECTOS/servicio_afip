# gunicorn_conf.py

# --- Configuración del Servidor ---
bind = "0.0.0.0:8002"
workers = 4

# --- Configuración de Logging ---
# Estas líneas son la clave. Le dicen a Gunicorn que capture
# todo lo que se imprima en la consola (stdout y stderr) y lo
# envíe a los logs del contenedor Docker.

capture_output = True
loglevel = "debug"
accesslog = "-"  # Envía logs de acceso a stdout
errorlog = "-"   # Envía logs de error a stderr