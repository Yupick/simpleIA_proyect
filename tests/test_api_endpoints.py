#!/usr/bin/env python3
"""
Script de pruebas para verificar los nuevos endpoints de API.
"""

import logging
import requests

logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"


def test_dashboard_endpoint():
    """Prueba el endpoint del dashboard."""
    logger.info("Probando /api/user/dashboard")
    try:
        response = requests.get(f"{BASE_URL}/api/user/dashboard")
        logger.info(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Productos: {data.get('products_count', 0)}")
            logger.info(f"Citas próximas: {data.get('upcoming_appointments', 0)}")
            logger.info(f"Tareas pendientes: {data.get('pending_tasks', 0)}")
            logger.info(f"Conversaciones: {data.get('conversations_count', 0)}")
        elif response.status_code == 401:
            logger.warning("Necesitas estar autenticado (esperado sin cookies)")
        else:
            logger.error(f"Error: {response.text}")
    except Exception:
        logger.exception("Error al probar dashboard endpoint")


def test_analytics_endpoint():
    """Prueba el endpoint de analytics."""
    logger.info("Probando /api/user/analytics")
    try:
        response = requests.get(f"{BASE_URL}/api/user/analytics?days=7")
        logger.info(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Tareas completadas: {data.get('tasks_completed', 0)}")
            logger.info(f"Total citas: {data.get('appointments_total', 0)}")
            logger.info(f"Productos: {data.get('products_total', 0)}")
        elif response.status_code == 401:
            logger.warning("Necesitas estar autenticado (esperado sin cookies)")
        else:
            logger.error(f"Error: {response.text}")
    except Exception:
        logger.exception("Error al probar analytics endpoint")


def test_whatsapp_endpoints():
    """Prueba los endpoints de WhatsApp."""
    logger.info("Probando endpoints de WhatsApp")

    endpoints = [
        ("GET", "/api/user/whatsapp/status"),
        ("GET", "/api/user/whatsapp/settings"),
        ("GET", "/api/user/whatsapp/logs"),
    ]

    for method, endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            status = "OK" if response.status_code in [200, 401] else "ERR"
            logger.info(f"{status} {method} {endpoint}: {response.status_code}")
        except Exception:
            logger.exception(f"Error calling {method} {endpoint}")


def test_reminders_endpoints():
    """Prueba los endpoints de recordatorios."""
    logger.info("Probando endpoints de Recordatorios")

    endpoints = [
        ("GET", "/api/user/reminders/preferences"),
        ("GET", "/api/user/reminders/history"),
    ]

    for method, endpoint in endpoints:
        try:
            response = requests.get(f"{BASE_URL}{endpoint}")
            status = "OK" if response.status_code in [200, 401] else "ERR"
            logger.info(f"{status} {method} {endpoint}: {response.status_code}")
        except Exception:
            logger.exception(f"Error calling {method} {endpoint}")


def test_server_running():
    """Verifica que el servidor esté corriendo."""
    logger.info("Verificando servidor")
    try:
        requests.get(f"{BASE_URL}/", timeout=2)
        logger.info(f"Servidor corriendo en {BASE_URL}")
        return True
    except requests.exceptions.ConnectionError:
        logger.error(f"Servidor NO está corriendo en {BASE_URL}")
        logger.info("Ejecuta: python app/llm_client.py")
        return False
    except Exception:
        logger.exception("Error verificando servidor")
        return False


def main():
    """Ejecuta todas las pruebas."""
    logger.info("PRUEBAS DE ENDPOINTS DE API - TEMPLATES")

    if not test_server_running():
        return

    # Probar endpoints
    test_dashboard_endpoint()
    test_analytics_endpoint()
    test_whatsapp_endpoints()
    test_reminders_endpoints()

    logger.info("NOTA: Los errores 401 son esperados si no estás autenticado.")
    logger.info("Para probar con autenticación, inicia sesión en el navegador")
    logger.info("y copia las cookies de sesión en tu herramienta de pruebas.")


if __name__ == "__main__":
    main()
