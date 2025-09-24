# app/afip_connector.py
import tempfile
import os
import ssl
from pysimplesoap.transport import Httplib2Transport
from pyafipws.wsaa import WSAA
from pyafipws.wsfev1 import WSFEv1
from app.config import URL_WSAA_PROD, URL_WSAA_HOMO, URL_WSFEv1_PROD, URL_WSFEv1_HOMO, CACHE
from app.logger_setup import logger

# --- BLOQUE COMPLETO Y SEGURO PARA FORZAR TLSv1.2 ---
# Esto se ejecuta una sola vez cuando el módulo es importado.
try:
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    context.load_default_certs()

    Httplib2Transport.SSL_CONTEXT = context
    logger.info("Contexto SSL forzado a TLSv1.2 exitosamente.")
except Exception as e:
    logger.warning(f"No se pudo forzar el contexto SSL a TLSv1.2. Error: {e}")


class AfipConnector:
    def __init__(self):
        self.wsfev1 = None
        self.cuit = None
        self.is_production = None

    def conectar(self, credenciales, production=True, force_reconnect=False):
        cuit = credenciales.get('cuit')
        if not cuit:
            raise ValueError("El CUIT no fue proporcionado en las credenciales.")

        if (self.wsfev1 and self.cuit == cuit and self.is_production == production 
            and not force_reconnect):
            logger.info(f"Reutilizando conexión para CUIT {cuit} en entorno {'PROD' if production else 'HOMO'}")
            return self.wsfev1

        if force_reconnect:
            logger.info(f"Forzando reconexión para CUIT {cuit}")
        else:
            logger.info(f"Creando nueva conexión para CUIT {cuit} en entorno {'PROD' if production else 'HOMO'}")
        
        self.cuit = cuit
        self.is_production = production
        cert_str = credenciales.get('certificado')
        key_str = credenciales.get('clave_privada')

        if not cert_str or not key_str:
            raise ValueError("Certificado o clave privada no proporcionados.")

        cert_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.crt', encoding='utf-8')
        key_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.key', encoding='utf-8')

        try:
            cert_file.write(cert_str)
            cert_file.close()
            key_file.write(key_str)
            key_file.close()

            wsaa = WSAA()
            URL_WSAA = URL_WSAA_PROD if production else URL_WSAA_HOMO

            # Forma correcta de autenticar: el resultado se guarda en el objeto wsaa
            wsaa.Autenticar(
                service="wsfe",
                crt=cert_file.name,
                key=key_file.name,
                wsdl=URL_WSAA,
                cache=CACHE,
                debug=True
            )

            self.wsfev1 = WSFEv1()
            self.wsfev1.Cuit = cuit
            # Forma correcta de asignar Token y Sign
            self.wsfev1.Token = wsaa.Token
            self.wsfev1.Sign = wsaa.Sign

            URL_WSFEv1 = URL_WSFEv1_PROD if production else URL_WSFEv1_HOMO
            self.wsfev1.Conectar(wsdl=URL_WSFEv1, cache=CACHE)

            logger.info(f"Conexión exitosa al endpoint del WSDL: {URL_WSFEv1}")
            return self.wsfev1
        
        except Exception as auth_error:
            # Manejo robusto de errores de autenticación
            error_str = str(auth_error).lower()
            error_type = type(auth_error).__name__
            
            logger.warning(f"Error de autenticación {error_type}: {auth_error}")
            
            # Detectar diferentes tipos de errores
            is_token_error = any(keyword in error_str for keyword in 
                               ["token", "validacion", "fechas", "gentime", "exptime"])
            
            is_ssl_error = (
                isinstance(auth_error, ssl.SSLError) or
                "ssl" in error_str or
                "certificate" in error_str or
                "handshake" in error_str
            )
            
            is_connection_error = (
                isinstance(auth_error, (ConnectionResetError, ConnectionError)) or
                "connection reset" in error_str or
                "not subscriptable" in error_str
            )
            
            # Intentar recuperación según el tipo de error
            if is_token_error or is_ssl_error or is_connection_error:
                logger.info(f"Detectado error recuperable: {error_type}. Limpiando cache...")
                try:
                    import glob
                    cache_files = glob.glob(f"{CACHE}/*")
                    for cache_file in cache_files:
                        os.remove(cache_file)
                    logger.info("Cache limpiado exitosamente")
                    
                    # Reintentar autenticación después de limpiar cache
                    wsaa.Autenticar(
                        service="wsfe",
                        crt=cert_file.name,
                        key=key_file.name,
                        wsdl=URL_WSAA,
                        cache=CACHE,
                        debug=True
                    )
                    
                    self.wsfev1 = WSFEv1()
                    self.wsfev1.Cuit = cuit
                    self.wsfev1.Token = wsaa.Token
                    self.wsfev1.Sign = wsaa.Sign
                    self.wsfev1.Conectar(wsdl=URL_WSFEv1, cache=CACHE)
                    logger.info("Reconexión exitosa después de limpiar cache")
                    
                except Exception as retry_error:
                    retry_error_msg = str(retry_error)
                    logger.error(f"Error en reintento después de limpiar cache: {retry_error_msg}")
                    # No usar indexación de errores, solo el mensaje string
                    if is_connection_error:
                        raise ConnectionError(f"Fallo de conexión en reintento: {retry_error_msg}")
                    else:
                        raise auth_error
            else:
                # Error no recuperable
                logger.error(f"Error no recuperable: {error_type}")
                raise auth_error
                
        finally:
            os.remove(cert_file.name)
            os.remove(key_file.name)

# Instancia única que importarán otros archivos
afip_conector = AfipConnector()