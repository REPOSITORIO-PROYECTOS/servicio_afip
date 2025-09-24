# convertir_credenciales.py
import json

print("\n--- Credenciales formateadas para JSON ---\n")

try:
    # Usa el nombre de TU archivo de certificado
    with open('SISTEMA IMA_37df1c7cae68b855.crt', 'r') as f:
        cert_content = f.read()
    print("Contenido para 'certificado':")
    print(json.dumps(cert_content))
    print("-" * 40)
except FileNotFoundError:
    print("ERROR: No se encontró el archivo 'caja_prueba_taup.crt'")

try:
    # Usa el nombre de TU archivo de clave
    with open('mi_clave_privada.key', 'r') as f:
        key_content = f.read()
    print("Contenido para 'clave_privada':")
    print(json.dumps(key_content))
    print("-" * 40)
except FileNotFoundError:
    print("ERROR: No se encontró el archivo 'mi_clave_privada.key'")

print("\nCopia y pega estas cadenas (incluidas las comillas) en tu archivo factura_test.json\n")
