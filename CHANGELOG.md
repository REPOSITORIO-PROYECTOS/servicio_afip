# Changelog

Todos los cambios notables en este proyecto serán documentados en este archivo.

## [2.4.0] - 2025-09-24

### 🚀 Mejoras Críticas de Conectividad y Robustez
- **Manejo Robusto de Errores de Conexión**: Implementado manejo específico para `ConnectionResetError`, `SSL errors` y `TypeError` con reintentos automáticos
- **Limpieza Automática de Cache**: Detección automática de tokens expirados y limpieza de cache sin intervención manual
- **Sistema de Reconexión Inteligente**: Reconexión automática en caso de fallas de conexión con AFIP
- **Respuesta JSON Completa**: Corregido el modelo de respuesta para incluir todos los campos esperados por el cliente

### 🔧 Correcciones de Bugs
- **Solucionado Error de Token Expirado**: Renovación automática de tokens AFIP cuando expiran
- **Eliminado TypeError en pyafipws**: Manejo correcto de excepciones sin usar indexación `e[0]`
- **Mejorado Manejo SSL/TLS**: Detección y recuperación automática de errores SSL
- **Corregida Estructura de Respuesta**: JSON de respuesta ahora coincide 100% con `factura_response_model`

### 📊 Logging y Debugging
- **Logs Detallados**: Agregado logging completo de datos recibidos para debugging
- **Trazabilidad de Errores**: Logs específicos para cada tipo de error y intento de recuperación
- **Monitoreo Mejorado**: Logs claros para identificar problemas de conectividad

### ⚡ Rendimiento
- **Reintentos Inteligentes**: Máximo 2 intentos por operación antes de fallar definitivamente  
- **Reutilización de Conexiones**: Mantiene conexiones válidas, fuerza reconexión solo cuando es necesario
- **Cache Optimizado**: Limpieza selectiva de cache solo cuando se detectan errores de token

### 🛡️ Robustez
- **Recuperación Automática**: El servicio se recupera automáticamente de la mayoría de errores temporales
- **Sin Intervención Manual**: Eliminada la necesidad de reiniciar manualmente el servicio por tokens expirados
- **Tolerancia a Fallas**: Continúa operando ante fallas de red temporales

## [2.3.0] - 2025-07-09

### Nuevas características
- **Consulta de Comprobantes**: Se agregó un nuevo endpoint `GET /api/afipws/consulta_comprobante` para consultar el estado y los datos de un comprobante ya emitido en AFIP.
- **Soporte para Python 3.13**: Se ha añadido configuración funcional para ejecutar la aplicación con Python 3.13.
- **Soporte para Python 3.12**: Se ha añadido configuración funcional para ejecutar la aplicación con Python 3.12.
- **Integración con OpenTelemetry**: para observabilidad, instrumentación automática de Flask, requests y logging.

### Mejoras
- **Dockerfile de Producción**: Se ha alineado el Dockerfile de producción para que sea compatible con Python 3.13.
- **Documentación**: Se añadieron diagramas de arquitectura y de secuencia (Mermaid) para ilustrar los flujos de los endpoints de facturación y consulta.

## [2.2.0] - 2025-07-06

### Nuevas características
- **Soporte para Python 3.13**: Se ha añadido configuración funcional para ejecutar la aplicación con Python 3.13.
- **Soporte para Python 3.12**: Se ha añadido configuración funcional para ejecutar la aplicación con Python 3.12.

### Mejoras
- **Dockerfile de Producción**: Se ha alineado el Dockerfile de producción para que sea compatible con Python 3.13.

## [2.1.0] - 2025-07-03

### Nuevas características
- **Consulta de Comprobantes**: Se agregó un nuevo endpoint `GET /api/afipws/consulta_comprobante` para consultar el estado y los datos de un comprobante ya emitido en AFIP.

### Mejoras
- **Respuesta de API Mejorada**: La respuesta del endpoint de consulta ahora devuelve una estructura JSON consistente, con un mensaje de AFIP y los datos de la factura, tanto para casos de éxito como para cuando el comprobante no se encuentra.
- **Documentación Automática**: Se añadieron diagramas de arquitectura y de secuencia (Mermaid) para ilustrar los flujos de los endpoints de facturación y consulta.
- **CI/CD**: Se actualizó el workflow de GitHub Actions para la generación de documentación, adaptándolo a un proyecto Python y añadiendo los nuevos diagramas.

### Correcciones
- **Llamada a Librería**: Se corrigió la llamada al método `CompConsultar` para usar los parámetros posicionales correctos que requiere la versión local de la librería `pyafipws`, solucionando el `TypeError`.
- **Manejo de Atributos**: Se corrigió el acceso al resultado de la consulta para usar el atributo `wsfev1.factura` en lugar del inexistente `ResultGet`, solucionando el `AttributeError`.

## [2025.06.14] - 2025-06-14

### Nuevas características
- **Integración completa con OpenTelemetry** para observabilidad
- **Instrumentación automática** de Flask, requests y logging
- **Soporte para trazas distribuidas** con Jaeger + Elasticsearch
- **Nuevo archivo `app/otel_setup.py`** para configuración de observabilidad

### Mejoras
- Actualizada documentación del README con información de observabilidad
- Mejorado el logging con contexto de trazas
- Agregadas dependencias OpenTelemetry:
  - opentelemetry-api==1.21.0
  - opentelemetry-sdk==1.21.0
  - opentelemetry-instrumentation-flask==0.42b0
  - opentelemetry-instrumentation-requests==0.42b0
  - opentelemetry-instrumentation-logging==0.42b0
  - opentelemetry-exporter-otlp-proto-http==1.21.0

### Cambios técnicos
- Modificado `app/service.py` para integrar OpenTelemetry
- Actualizado `app/routes.py` para incluir trazas en endpoints
- Agregada configuración opcional via variable de entorno `OTEL_EXPORTER_OTLP_ENDPOINT`

## [2025.05.18] - 2025-05-18

### Mejoras
- Actualizado Python a 3.11
- Actualizada versión de pyafipws a v2025.05.05
- Mejorada la documentación del proyecto

### Cambios
- Agregado campo requerido `id_condicion_iva` para facturación
- Mejorado el formato de logging de JSON en el endpoint de facturación

## [2025.01.03] - 2025-01-03

### Mejoras
- Mejorado el logging de la integración con AFIP
- Deshabilitado el cache para la integración con AFIP

## [2025.01.01] - 2025-01-01

### Mejoras
- Restaurada la verificación de estado de servidores AFIP
- Mejorado el manejo de autenticación

### Correcciones
- Removido logging de debug hardcodeado
- Corregido el nivel de debug para conexiones HTTP

## Notas
- Todos los cambios están basados en commits reales del repositorio verificados en el historial de git
- Las fechas están en formato YYYY-MM-DD y corresponden a las fechas reales de los commits
- Los cambios están organizados cronológicamente de más reciente a más antiguo
- Información no verificable del historial anterior ha sido removida para mantener precisión

### Información no verificable removida
- Cambios fechados en 2024.07.25, 2024.09.14, 2024.11.07, 2024.12.02, 2025.01.14 no pudieron ser confirmados en el historial de git actual
- Se recomienda verificar estos cambios con el historial completo del repositorio
