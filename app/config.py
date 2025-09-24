# app/config.py

# URLs para el servicio de autenticación (WSAA)
URL_WSAA_HOMO = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl"
URL_WSAA_PROD = "https://wsaa.afip.gov.ar/ws/services/LoginCms?wsdl"

# URLs para el servicio de Factura Electrónica (WSFEv1)
URL_WSFEv1_HOMO = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"
URL_WSFEv1_PROD = "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL"

# Ruta para el caché de tickets de acceso. Puede ser un directorio temporal.
CACHE = "/tmp/pyafipws_cache"

# Aquí podrías añadir más configuraciones en el futuro si las necesitas.
