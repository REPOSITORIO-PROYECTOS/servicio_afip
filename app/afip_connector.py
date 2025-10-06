# app/afip_connector.py
import tempfile
import os
import ssl
from pysimplesoap.transport import Httplib2Transport
from pyafipws.wsaa import WSAA
from pyafipws.wsfev1 import WSFEv1
from app.config import URL_WSAA_PROD, URL_WSAA_HOMO, URL_WSFEv1_PROD, URL_WSFEv1_HOMO, CACHE
from app.logger_setup import logger
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.backends import default_backend

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

        # Validar rápidamente el contenido PEM antes de escribir y llamar a WSAA
        try:
            # Intentamos cargar la clave privada PEM para validar formato
            load_pem_private_key(key_str.encode('utf-8'), password=None, backend=default_backend())
        except Exception as pem_err:
            logger.warning(f"Clave privada inválida o en formato no soportado: {pem_err}")
            raise ValueError("Clave privada en formato PEM inválida o no soportada")

        try:
            # Intento básico de validar certificado (puede que sea una cadena que contenga encabezados PEM)
            # Cargamos el certificado como una clave pública para validar formato PEM básico.
            # Si esto falla no necesariamente es fatal (puede ser certificado x509), pero lo intentamos.
            try:
                load_pem_public_key(cert_str.encode('utf-8'), backend=default_backend())
            except Exception:
                # No es una clave pública PEM; no forzamos fallo porque algunos CRTs contienen certificados X.509
                # y la validación estricta se delegará a la librería que firma.
                logger.debug("Advertencia: no se pudo parsear certificado como clave pública PEM — se continuará y dejará que WSAA valide.")

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
            # Si la excepción es por formato/entrada inválida (ValueError) la re-lanzamos
            # para que la capa de negocio y de rutas puedan devolver un 400 al cliente.
            if isinstance(auth_error, ValueError):
                logger.warning(f"Error de entrada detectado al autenticar: {auth_error}")
                raise
            # Manejo robusto de errores de autenticación
            error_str = str(auth_error).lower()
            error_type = type(auth_error).__name__

            logger.warning(f"Error de autenticación {error_type}: {auth_error}")

            # Caso especial: AFIP indica que el CEE ya posee un TA válido.
            # En esa situación preferimos reutilizar el TA más reciente que esté
            # presente en la carpeta de cache en vez de fallar o eliminarlo.
            if "alreadyauthenticated" in error_str or "already authenticated" in error_str:
                try:
                    import glob
                    import xml.etree.ElementTree as ET

                    ta_files = glob.glob(f"{CACHE}/TA-*.xml")
                    if ta_files:
                        ta_files.sort(key=os.path.getmtime, reverse=True)
                        latest_ta = ta_files[0]
                        logger.info(f"Reutilizando TA existente desde cache: {latest_ta}")
                        tree = ET.parse(latest_ta)
                        root = tree.getroot()
                        # Intentar extraer token y sign desde la estructura estándar
                        token_el = root.find('.//token')
                        sign_el = root.find('.//sign')
                        token_text = token_el.text.strip() if token_el is not None and token_el.text else None
                        sign_text = sign_el.text.strip() if sign_el is not None and sign_el.text else None

                        if token_text and sign_text:
                            self.wsfev1 = WSFEv1()
                            self.wsfev1.Cuit = cuit
                            self.wsfev1.Token = token_text
                            self.wsfev1.Sign = sign_text
                            self.wsfev1.Conectar(wsdl=URL_WSFEv1, cache=CACHE)
                            logger.info("Conexión exitosa reutilizando TA existente")
                            return self.wsfev1
                        else:
                            logger.warning("TA encontrada pero no se pudo extraer Token/Sign; proceder con reintento")
                    else:
                        logger.info("No se encontró TA en cache para reutilizar")
                except Exception as e:
                    logger.warning(f"Fallo al intentar reutilizar TA existente: {e}")

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