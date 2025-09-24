# app.py
from flask import Flask
from flask_restx import Api
from app.routes import register_routes  # Importa la función de registro
import os

# 1. Crear la instancia de la aplicación Flask
app = Flask(__name__)

# 2. Crear la instancia de la API de Flask-RESTX
api = Api(app,
          version='1.0',
          title='Microservicio de Facturación AFIP',
          description='Una API para interactuar con los web services de AFIP.')

# 3. Configuración (esto es lo que se pasará a tus rutas)
# Puedes mover esto a un archivo de configuración o variables de entorno más adelante
afip_config = {
    # Esta línea ahora leerá 'TRUE' y 'production' será True
    "production": os.environ.get('PRODUCTION', 'False').lower() == 'true',
}

# 4. Registrar las rutas
register_routes(afip_config, api)

# 5. Punto de entrada para ejecutar la aplicación
if __name__ == '__main__':
    # Esto es para desarrollo local, no para producción con Gunicorn
    app.run(host='0.0.0.0', port=8001, debug=True)
