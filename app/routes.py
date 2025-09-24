import json
from flask import request
from flask_restx import Namespace, Resource, fields
from app.logger_setup import logger
from app.factura_electronica import facturar
from app.otel_setup import get_tracer
from typing import Dict

# Crear namespace para Flask-RESTX
afipws_ns = Namespace('afipws', description='Operaciones de facturación AFIP')

# Variable global para almacenar la configuración
_afip_config = {}

credenciales_model = afipws_ns.model('Credenciales', {
    'cuit': fields.String(required=True, description='CUIT del emisor de la factura', example='20123456789'),
    'certificado': fields.String(required=True, description='Contenido del archivo de certificado (.crt) en formato string'),
    'clave_privada': fields.String(required=True, description='Contenido del archivo de clave privada (.key) en formato string')
})  


# Modelos para Swagger
factura_data_model = afipws_ns.model('DatosFactura', {
    'tipo_afip': fields.Integer(required=True, description='Tipo de comprobante AFIP', example=1),
    'punto_venta': fields.Integer(required=True, description='Punto de venta', example=1),
    'tipo_documento': fields.Integer(required=True, description='Tipo de documento del receptor', example=80),
    'documento': fields.String(required=True, description='Número de documento del receptor', example='20123456789'),
    'total': fields.Float(required=True, description='Importe total', example=1210.0),
    'id_condicion_iva': fields.Integer(required=True, description='ID de condición IVA del receptor', example=1),
    'neto': fields.Float(description='Importe neto gravado', example=1000.0),
    'iva': fields.Float(description='Importe IVA 21%', example=210.0),
    'neto105': fields.Float(description='Importe neto gravado 10.5%', example=0.0),
    'iva105': fields.Float(description='Importe IVA 10.5%', example=0.0),
    'asociado_tipo_afip': fields.Integer(description='Tipo de comprobante asociado'),
    'asociado_punto_venta': fields.Integer(description='Punto de venta del comprobante asociado'),
    'asociado_numero_comprobante': fields.Integer(description='Número de comprobante asociado'),
    'asociado_fecha_comprobante': fields.String(description='Fecha del comprobante asociado')
})

factura_multitenant_model = afipws_ns.model('FacturaMultiTenant', {
    'credenciales': fields.Nested(credenciales_model, required=True),
    'datos_factura': fields.Nested(factura_data_model, required=True)
})


response_model = afipws_ns.model('Response', {
    'success': fields.Boolean(description='Indica si la operación fue exitosa'),
    'data': fields.Raw(description='Datos de respuesta'),
    'error': fields.String(description='Mensaje de error si aplica')
})

factura_response_model = afipws_ns.model('FacturaResponse', {
    'tipo_documento': fields.Integer(description='Tipo de documento del receptor'),
    'documento': fields.String(description='Número de documento del receptor'),
    'tipo_afip': fields.Integer(description='Tipo de comprobante AFIP'),
    # ... (el resto de los campos de tu factura_response_model se quedan igual) ...
    'punto_venta': fields.Integer(description='Punto de venta'),
    'total': fields.Float(description='Importe total'),
    'exento': fields.Float(description='Importe exento'),
    'neto': fields.Float(description='Importe neto gravado'),
    'neto105': fields.Float(description='Importe neto gravado 10.5%'),
    'iva': fields.Float(description='Importe IVA 21%'),
    'iva105': fields.Float(description='Importe IVA 10.5%'),
    'resultado': fields.String(description='Resultado de la autorización'),
    'cae': fields.String(description='Número de CAE'),
    'vencimiento_cae': fields.String(description='Fecha de vencimiento del CAE'),
    'numero_comprobante': fields.Integer(description='Número de comprobante'),
    'fecha_comprobante': fields.String(description='Fecha del comprobante'),
    'asociado_tipo_afip': fields.Integer(description='Tipo de comprobante asociado'),
    'asociado_punto_venta': fields.Integer(description='Punto de venta del comprobante asociado'),
    'asociado_numero_comprobante': fields.Integer(description='Número de comprobante asociado'),
    'asociado_fecha_comprobante': fields.String(description='Fecha del comprobante asociado'),
    'id_condicion_iva': fields.Integer(description='ID de condición IVA del receptor')
})

test_response_model = afipws_ns.model('TestResponse', {
    'test': fields.String(description='Mensaje de prueba', example='ok')
})

consulta_parser = afipws_ns.parser()
consulta_parser.add_argument('tipo_cbte', type=int, required=True, help='Tipo de comprobante AFIP', location='args')
consulta_parser.add_argument('punto_vta', type=int, required=True, help='Punto de venta', location='args')
consulta_parser.add_argument('cbte_nro', type=int, required=True, help='Número de comprobante', location='args')

consulta_response_model = afipws_ns.model('ConsultaResponse', {
    'mensaje': fields.String(description='Mensaje devuelto por AFIP'),
    'factura': fields.Raw(description='Datos del comprobante consultado (si existe)', required=False)
})


@afipws_ns.route('/test')
class TestResource(Resource):
    @afipws_ns.doc('test_endpoint')
    @afipws_ns.marshal_with(test_response_model)
    def get(self):
        """Endpoint de prueba para verificar el estado del servicio."""
        tracer = get_tracer()
        if tracer:
            with tracer.start_as_current_span("test_endpoint") as span:
                span.set_attribute("endpoint", "/test")
                span.set_attribute("method", "GET")
                logger.info("test")
                return {"test": "ok"}
        else:
            logger.info("test")
            return {"test": "ok"}





@afipws_ns.route('/facturador')
class FacturadorResource(Resource):
    @afipws_ns.doc('facturar')
    # ¡CAMBIO CLAVE! Ahora esperamos el nuevo modelo combinado.
    @afipws_ns.expect(factura_multitenant_model) 
    # La respuesta sigue usando el mismo modelo que antes.
    @afipws_ns.marshal_with(factura_response_model)
    def post(self):
        """Endpoint multi-tenant para procesar facturas electrónicas AFIP."""
        try:
            json_data = request.get_json()
            if json_data is None:
                afipws_ns.abort(400, "No se proporcionó un JSON válido")

            # Separamos las credenciales y los datos de la factura del payload
            credenciales = json_data.get('credenciales')
            datos_factura = json_data.get('datos_factura')

            if not credenciales or not datos_factura:
                afipws_ns.abort(400, "El JSON debe contener los objetos anidados 'credenciales' y 'datos_factura'")
            
            logger.info(f"Facturando para CUIT: {credenciales.get('cuit')}...")
            
            # DEBUG: Logear los datos recibidos para análisis
            logger.info(f"DATOS RECIBIDOS - Credenciales CUIT: {credenciales.get('cuit')}")
            logger.info(f"DATOS RECIBIDOS - Datos factura: {datos_factura}")
            
            # Obtener la configuración global de 'production'
            production = _afip_config.get('production', False)
            
            # ¡CAMBIO CLAVE! Pasamos las credenciales y los datos de la factura 
            # a la función de negocio para que ella los maneje.
            result = facturar(credenciales, datos_factura)
            
            return result
            
        except Exception as e:
            # --- BLOQUE DE DEPURACIÓN MEJORADO ---
            error_type = type(e).__name__
            error_message = str(e)
            
            # Imprimimos todos los detalles en el log para la autopsia
            logger.error(f'!!!!!!!! ERROR FATAL ENCONTRADO !!!!!!!!')
            logger.error(f'TIPO DE EXCEPCIÓN: {error_type}')
            logger.error(f'MENSAJE DE EXCEPCIÓN: {error_message}')
            # Usamos exc_info=True para que el logger imprima el traceback completo
            logger.error('TRACEBACK COMPLETO:', exc_info=True)
            
            # Devolvemos una respuesta clara al cliente
            error_completo = f"{error_type}: {error_message}"
            afipws_ns.abort(500, message=f"Error interno del servidor: {error_completo}")
            # ------------------------------------

            

def register_routes(config: Dict, api):
    """Configura y registra las rutas con la API de Flask-RESTX."""
    # Guardar la configuración en la variable global
    global _afip_config
    _afip_config = config
    
    # Agregar namespace a la API
    api.add_namespace(afipws_ns)