# app/factura_electronica.py
import datetime
import ssl
from typing import Dict, Any
import logging
from app.logger_setup import logger
from app.afip_connector import afip_conector

def facturar(credenciales: Dict[str, str], datos_factura: Dict[str, Any], production: bool = True) -> Dict[str, Any]:
    """
    Emite facturas electrónicas con CAE AFIP utilizando un conector dinámico.
    """
    logger.debug(f"Iniciando facturación para CUIT: {credenciales.get('cuit')}")
    logging.basicConfig(level=logging.DEBUG)

    # Intentar conectar con reintentos en caso de problemas de conexión
    max_reintentos = 2
    for intento in range(max_reintentos):
        try:
            force_reconnect = intento > 0  # Forzar reconexión en reintentos
            wsfev1 = afip_conector.conectar(credenciales, production=True, force_reconnect=force_reconnect)
            break
        except Exception as e:
            # Si la excepción es ValueError (p. ej. PEM inválido), considerarla error de entrada
            logger.error(f"Intento {intento + 1}/{max_reintentos} - Fallo al conectar/autenticar con AFIP: {e}")
            if isinstance(e, ValueError):
                # Propagar ValueError para que la capa de rutas retorne 400
                raise
            if intento == max_reintentos - 1:  # Último intento
                logger.error(f"Fallo definitivo de autenticación AFIP después de {max_reintentos} intentos", exc_info=True)
                raise RuntimeError(f"Fallo de autenticación AFIP: {e}")

    try:
        tipo_cbte = datos_factura.get("tipo_afip")
        punto_vta = datos_factura.get("punto_venta")
        
        # Intentar obtener último comprobante con manejo robusto de errores
        max_reintentos_operacion = 2
        for intento_op in range(max_reintentos_operacion):
            try:
                ultimo_cbte = wsfev1.CompUltimoAutorizado(tipo_cbte, punto_vta)
                break
            except TypeError as conn_error:
                # Algunos errores (p. ej. en pyafipws) lanzan TypeError al indexar excepciones internas.
                error_msg = str(conn_error)
                error_type = type(conn_error).__name__
                logger.warning(f"TypeError tratado como error de conexión al consultar último comprobante (intento {intento_op + 1}): {error_msg}")
                if intento_op < max_reintentos_operacion - 1:
                    logger.info(f"Forzando reconexión debido a TypeError (intento {intento_op + 1})...")
                    wsfev1 = afip_conector.conectar(credenciales, production=True, force_reconnect=True)
                    continue
                else:
                    raise ConnectionError(f"Fallo de conexión por TypeError después de {max_reintentos_operacion} intentos: {error_msg}")
            except Exception as conn_error:
                # Manejo robusto de diferentes tipos de error
                error_msg = str(conn_error)
                error_type = type(conn_error).__name__
                
                logger.warning(f"Error {error_type} al consultar último comprobante (intento {intento_op + 1}): {error_msg}")
                
                # Detectar errores de conexión/SSL
                is_connection_error = (
                    isinstance(conn_error, (ConnectionResetError, ConnectionError)) or
                    "Connection reset by peer" in error_msg or
                    "SSL" in error_msg or
                    "ssl" in error_msg.lower() or
                    "not subscriptable" in error_msg
                )
                
                if is_connection_error and intento_op < max_reintentos_operacion - 1:
                    logger.info(f"Detectado error de conexión. Intentando reconectar (intento {intento_op + 1})...")
                    # Forzar reconexión
                    wsfev1 = afip_conector.conectar(credenciales, production=True, force_reconnect=True)
                else:
                    # Si no es error de conexión o ya agotamos reintentos, re-lanzar
                    if is_connection_error:
                        raise ConnectionError(f"Fallo de conexión después de {max_reintentos_operacion} intentos: {error_msg}")
                    else:
                        raise conn_error
        
        siguiente_cbte = int(ultimo_cbte) + 1
        logger.info(f"Último comprobante fue {ultimo_cbte}. Siguiente a emitir: {siguiente_cbte}.")

        total = float(datos_factura.get("total", 0.0))
        
        # Lógica de importes
        imp_neto = float(datos_factura.get("neto", 0.0))
        imp_iva = float(datos_factura.get("iva", 0.0))
        imp_tot_conc = 0.0
        imp_op_ex = 0.0

        if tipo_cbte in [11, 12, 13]:
            # Para Facturas C, el total va en el campo de Neto.
            imp_neto = total
            # Todos los otros campos de importes deben ser cero, como lo pide AFIP.
            imp_iva = 0.0
            imp_tot_conc = 0.0
 

        wsfev1.CrearFactura(
            concepto=1,
            tipo_doc=datos_factura.get("tipo_documento"),
            nro_doc=datos_factura.get("documento"),
            tipo_cbte=tipo_cbte,
            punto_vta=punto_vta,
            cbt_desde=siguiente_cbte,
            cbt_hasta=siguiente_cbte,
            imp_total=total,
            imp_neto=imp_neto,
            imp_iva=imp_iva,
            imp_tot_conc=imp_tot_conc,
            imp_op_ex=imp_op_ex,
            fecha_cbte=datetime.date.today().strftime("%Y%m%d")
        )


        if imp_neto > 0 and not (tipo_cbte in [11, 12, 13]):
            if imp_iva > 0:
                logger.info(f"Agregando detalle de IVA (21%) sobre base {imp_neto}")
                wsfev1.AgregarIva(5, round(imp_neto,2), round(imp_iva,2))
            else:
                logger.info(f"Agregando detalle de IVA (0%) sobre base {imp_neto}")
                wsfev1.AgregarIva(3, round(imp_neto,2), 0.0)

        logger.info("Solicitando CAE a AFIP...")

        # Intentar solicitar CAE con manejo robusto de errores
        max_reintentos_cae = 2
        for intento_cae in range(max_reintentos_cae):
            try:
                wsfev1.CAESolicitar()
                break
            except TypeError as cae_error:
                # Capturamos TypeError originados por la librería externa y los tratamos como errores de conexión
                error_msg = str(cae_error)
                logger.warning(f"TypeError tratado como error de conexión al solicitar CAE (intento {intento_cae + 1}): {error_msg}")
                if intento_cae < max_reintentos_cae - 1:
                    logger.info(f"Forzando reconexión por TypeError en CAE (intento {intento_cae + 1})...")
                    wsfev1 = afip_conector.conectar(credenciales, production=True, force_reconnect=True)
                    # Recrear factura
                    wsfev1.CrearFactura(
                        concepto=1,
                        tipo_doc=datos_factura.get("tipo_documento"),
                        nro_doc=datos_factura.get("documento"),
                        tipo_cbte=tipo_cbte,
                        punto_vta=punto_vta,
                        cbt_desde=siguiente_cbte,
                        cbt_hasta=siguiente_cbte,
                        imp_total=total,
                        imp_neto=imp_neto,
                        imp_iva=imp_iva,
                        imp_tot_conc=imp_tot_conc,
                        imp_op_ex=imp_op_ex,
                        fecha_cbte=datetime.date.today().strftime("%Y%m%d")
                    )
                    if imp_neto > 0 and not (tipo_cbte in [11, 12, 13]):
                        if imp_iva > 0:
                            logger.info("Reagregando IVA 21% después de reconexión por TypeError")
                            wsfev1.AgregarIva(5, round(imp_neto,2), round(imp_iva,2))
                        else:
                            logger.info("Reagregando IVA 0% después de reconexión por TypeError")
                            wsfev1.AgregarIva(3, round(imp_neto,2), 0.0)
                    continue
                else:
                    raise ConnectionError(f"Fallo de conexión por TypeError en CAE después de {max_reintentos_cae} intentos: {error_msg}")
            except Exception as cae_error:
                # Manejo robusto de diferentes tipos de error
                error_msg = str(cae_error)
                error_type = type(cae_error).__name__
                
                logger.warning(f"Error {error_type} al solicitar CAE (intento {intento_cae + 1}): {error_msg}")
                
                # Detectar errores de conexión/SSL
                is_connection_error = (
                    isinstance(cae_error, (ConnectionResetError, ConnectionError)) or
                    "Connection reset by peer" in error_msg or
                    "SSL" in error_msg or
                    "ssl" in error_msg.lower() or
                    "not subscriptable" in error_msg
                )
                
                if is_connection_error and intento_cae < max_reintentos_cae - 1:
                    logger.info(f"Detectado error de conexión en CAE. Reconectando y recreando factura (intento {intento_cae + 1})...")
                    
                    # Forzar reconexión
                    wsfev1 = afip_conector.conectar(credenciales, production=True, force_reconnect=True)
                    
                    # Recrear la factura completa después de reconectar
                    wsfev1.CrearFactura(
                        concepto=1,
                        tipo_doc=datos_factura.get("tipo_documento"),
                        nro_doc=datos_factura.get("documento"),
                        tipo_cbte=tipo_cbte,
                        punto_vta=punto_vta,
                        cbt_desde=siguiente_cbte,
                        cbt_hasta=siguiente_cbte,
                        imp_total=total,
                        imp_neto=imp_neto,
                        imp_iva=imp_iva,
                        imp_tot_conc=imp_tot_conc,
                        imp_op_ex=imp_op_ex,
                        fecha_cbte=datetime.date.today().strftime("%Y%m%d")
                    )
                    
                    # Reagregar IVA si corresponde
                    if imp_neto > 0 and not (tipo_cbte in [11, 12, 13]):
                        if imp_iva > 0:
                            logger.info("Reagregando IVA 21% después de reconexión")
                            wsfev1.AgregarIva(5, round(imp_neto,2), round(imp_iva,2))
                        else:
                            logger.info("Reagregando IVA 0% después de reconexión")
                            wsfev1.AgregarIva(3, round(imp_neto,2), 0.0)
                else:
                    # Si no es error de conexión o ya agotamos reintentos, re-lanzar
                    if is_connection_error:
                        raise ConnectionError(f"Fallo de conexión en CAE después de {max_reintentos_cae} intentos: {error_msg}")
                    else:
                        raise cae_error

        if wsfev1.Resultado != "A":
            errores = ". ".join(filter(None, wsfev1.Observaciones + wsfev1.Errores))
            raise RuntimeError(f"AFIP rechazó la factura: {errores}")
        
        logger.info(f"¡Factura autorizada! Nro: {wsfev1.CbteNro}, CAE: {wsfev1.CAE}")

        # Retornar JSON completo que coincida con el modelo factura_response_model
        return {
            "tipo_documento": datos_factura.get("tipo_documento"),
            "documento": datos_factura.get("documento"),
            "tipo_afip": datos_factura.get("tipo_afip"),
            "punto_venta": datos_factura.get("punto_venta"),
            "total": float(datos_factura.get("total", 0.0)),
            "exento": float(datos_factura.get("exento", 0.0)),
            "neto": float(datos_factura.get("neto", 0.0)),
            "neto105": float(datos_factura.get("neto105", 0.0)),
            "iva": float(datos_factura.get("iva", 0.0)),
            "iva105": float(datos_factura.get("iva105", 0.0)),
            "resultado": wsfev1.Resultado,
            "cae": wsfev1.CAE,
            "vencimiento_cae": wsfev1.Vencimiento,
            "numero_comprobante": int(wsfev1.CbteNro),
            "fecha_comprobante": datetime.date.today().strftime("%Y-%m-%d"),
            "asociado_tipo_afip": datos_factura.get("asociado_tipo_afip"),
            "asociado_punto_venta": datos_factura.get("asociado_punto_venta"),
            "asociado_numero_comprobante": datos_factura.get("asociado_numero_comprobante"),
            "asociado_fecha_comprobante": datos_factura.get("asociado_fecha_comprobante"),
            "id_condicion_iva": datos_factura.get("id_condicion_iva")
        }

    except Exception as e:
        logger.error(f"Error durante el proceso de facturación: {e}", exc_info=True)
        raise e