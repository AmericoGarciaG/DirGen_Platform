#!/usr/bin/env python3
"""
Script de prueba para verificar el Toolbelt completo del Orquestador
Verifica que readFile, writeFile, y listFiles funcionen correctamente
"""

import requests
import json
import os
import time

HOST = "http://127.0.0.1:8000"

def test_toolbelt():
    """Prueba integral del Toolbelt"""
    print("🔧 Iniciando pruebas del Toolbelt DirGen...")
    
    # Test 1: listFiles - Listar el directorio raíz
    print("\n1️⃣ Probando listFiles en directorio raíz...")
    try:
        response = requests.post(f"{HOST}/v1/tools/filesystem/listFiles", 
                               json={"path": "."}, timeout=10)
        result = response.json()
        print(f"✅ listFiles (raíz): {result.get('success', False)}")
        if result.get('success'):
            print(f"   📁 Directorios: {len(result.get('directories', []))}")
            print(f"   📄 Archivos: {len(result.get('files', []))}")
    except Exception as e:
        print(f"❌ listFiles (raíz): {e}")
    
    # Test 2: writeFile - Crear archivo de prueba
    print("\n2️⃣ Probando writeFile...")
    test_content = """# Test File
Este es un archivo de prueba para verificar writeFile.
Timestamp: """ + str(time.time())
    
    try:
        response = requests.post(f"{HOST}/v1/tools/filesystem/writeFile",
                               json={"path": "test_toolbelt_file.md", "content": test_content}, 
                               timeout=10)
        result = response.json()
        print(f"✅ writeFile: {result.get('success', False)}")
        if not result.get('success'):
            print(f"   Error: {result.get('error', 'Unknown')}")
    except Exception as e:
        print(f"❌ writeFile: {e}")
    
    # Test 3: readFile - Leer el archivo que acabamos de crear
    print("\n3️⃣ Probando readFile...")
    try:
        response = requests.post(f"{HOST}/v1/tools/filesystem/readFile",
                               json={"path": "test_toolbelt_file.md"}, timeout=10)
        result = response.json()
        print(f"✅ readFile: {result.get('success', False)}")
        if result.get('success'):
            content = result.get('content', '')
            print(f"   📄 Contenido: {len(content)} caracteres")
            if "Test File" in content:
                print("   ✅ Contenido correcto verificado")
            else:
                print("   ❌ Contenido no coincide")
        else:
            print(f"   Error: {result.get('error', 'Unknown')}")
    except Exception as e:
        print(f"❌ readFile: {e}")
    
    # Test 4: listFiles - Verificar que el archivo aparece
    print("\n4️⃣ Verificando que el archivo aparece en listFiles...")
    try:
        response = requests.post(f"{HOST}/v1/tools/filesystem/listFiles", 
                               json={"path": "."}, timeout=10)
        result = response.json()
        if result.get('success'):
            files = result.get('files', [])
            test_file_found = any('test_toolbelt_file.md' in f for f in files)
            print(f"✅ Archivo encontrado en listFiles: {test_file_found}")
        else:
            print(f"❌ listFiles falló: {result.get('error', 'Unknown')}")
    except Exception as e:
        print(f"❌ listFiles (verificación): {e}")
    
    # Test 5: Pruebas de seguridad - Path traversal
    print("\n5️⃣ Probando validación de seguridad...")
    security_tests = [
        {"path": "../../../etc/passwd", "description": "Path traversal con ../"},
        {"path": "/etc/passwd", "description": "Ruta absoluta"},
        {"path": "test/../../../etc/passwd", "description": "Path traversal combinado"},
    ]
    
    for test in security_tests:
        try:
            response = requests.post(f"{HOST}/v1/tools/filesystem/readFile",
                                   json={"path": test["path"]}, timeout=10)
            result = response.json()
            success = result.get('success', True)  # True sería malo para estas pruebas
            if not success and "inválida o insegura" in result.get('error', ''):
                print(f"   ✅ {test['description']}: Correctamente bloqueado")
            else:
                print(f"   ❌ {test['description']}: VULNERABILIDAD - {result}")
        except Exception as e:
            print(f"   ⚠️ {test['description']}: Error de conexión - {e}")
    
    # Cleanup
    print("\n🧹 Limpiando archivo de prueba...")
    try:
        if os.path.exists("test_toolbelt_file.md"):
            os.remove("test_toolbelt_file.md")
            print("✅ Archivo de prueba eliminado")
    except Exception as e:
        print(f"⚠️ Error eliminando archivo de prueba: {e}")
    
    print("\n🎉 Pruebas del Toolbelt completadas!")

if __name__ == "__main__":
    print("NOTA: Asegúrate de que el Orquestador esté ejecutándose en http://127.0.0.1:8000")
    print("Para iniciar el orquestador: python mcp_host/main.py\n")
    
    try:
        # Verificar que el orquestador esté ejecutándose
        response = requests.get(f"{HOST}/health", timeout=5)
        if response.status_code == 200:
            test_toolbelt()
        else:
            print("❌ El Orquestador no está respondiendo correctamente")
    except requests.exceptions.ConnectionError:
        print("❌ No se puede conectar al Orquestador. ¿Está ejecutándose?")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")