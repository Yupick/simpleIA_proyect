#!/usr/bin/env python3
"""
Script de pruebas para verificar los nuevos endpoints de API.
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_dashboard_endpoint():
    """Prueba el endpoint del dashboard."""
    print("\n=== Probando /api/user/dashboard ===")
    try:
        response = requests.get(f"{BASE_URL}/api/user/dashboard")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Productos: {data.get('products_count', 0)}")
            print(f"✅ Citas próximas: {data.get('upcoming_appointments', 0)}")
            print(f"✅ Tareas pendientes: {data.get('pending_tasks', 0)}")
            print(f"✅ Conversaciones: {data.get('conversations_count', 0)}")
        elif response.status_code == 401:
            print("⚠️  Necesitas estar autenticado (esperado sin cookies)")
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_analytics_endpoint():
    """Prueba el endpoint de analytics."""
    print("\n=== Probando /api/user/analytics ===")
    try:
        response = requests.get(f"{BASE_URL}/api/user/analytics?days=7")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Tareas completadas: {data.get('tasks_completed', 0)}")
            print(f"✅ Total citas: {data.get('appointments_total', 0)}")
            print(f"✅ Productos: {data.get('products_total', 0)}")
        elif response.status_code == 401:
            print("⚠️  Necesitas estar autenticado (esperado sin cookies)")
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")


def test_whatsapp_endpoints():
    """Prueba los endpoints de WhatsApp."""
    print("\n=== Probando endpoints de WhatsApp ===")
    
    endpoints = [
        ("GET", "/api/user/whatsapp/status"),
        ("GET", "/api/user/whatsapp/settings"),
        ("GET", "/api/user/whatsapp/logs"),
    ]
    
    for method, endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            status = "✅" if response.status_code in [200, 401] else "❌"
            print(f"{status} {method} {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ {method} {endpoint}: {e}")


def test_reminders_endpoints():
    """Prueba los endpoints de recordatorios."""
    print("\n=== Probando endpoints de Recordatorios ===")
    
    endpoints = [
        ("GET", "/api/user/reminders/preferences"),
        ("GET", "/api/user/reminders/history"),
    ]
    
    for method, endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            status = "✅" if response.status_code in [200, 401] else "❌"
            print(f"{status} {method} {endpoint}: {response.status_code}")
        except Exception as e:
            print(f"❌ {method} {endpoint}: {e}")


def test_server_running():
    """Verifica que el servidor esté corriendo."""
    print("\n=== Verificando servidor ===")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=2)
        print(f"✅ Servidor corriendo en {BASE_URL}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"❌ Servidor NO está corriendo en {BASE_URL}")
        print("   Ejecuta: python app/llm_client.py")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Ejecuta todas las pruebas."""
    print("╔═══════════════════════════════════════════════════════╗")
    print("║   PRUEBAS DE ENDPOINTS DE API - TEMPLATES            ║")
    print("╚═══════════════════════════════════════════════════════╝")
    
    if not test_server_running():
        return
    
    # Probar endpoints
    test_dashboard_endpoint()
    test_analytics_endpoint()
    test_whatsapp_endpoints()
    test_reminders_endpoints()
    
    print("\n" + "="*60)
    print("NOTA: Los errores 401 son esperados si no estás autenticado.")
    print("Para probar con autenticación, inicia sesión en el navegador")
    print("y copia las cookies de sesión.")
    print("="*60)


if __name__ == "__main__":
    main()
