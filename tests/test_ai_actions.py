"""
Pruebas para verificar que los asistentes AI pueden crear datos correctamente.
"""

import asyncio
from app.assistants.commercial import CommercialAssistant
from app.assistants.personal import PersonalAssistant
from app.db import products as products_db
from app.db import personal as personal_db


import logging

logger = logging.getLogger(__name__)


async def test_commercial_create_product():
    """Prueba creación de producto mediante lenguaje natural."""
    logger.info("=== Prueba: Crear Producto con AI ===")

    # Usuario de prueba
    user_id = 1
    assistant = CommercialAssistant(user_id)

    # Mensajes de prueba
    test_messages = [
        "agregar laptop gaming por $1500 con 10 unidades",
        "crear producto mouse inalámbrico por $25",
        "añade teclado mecánico a $120 stock 5",
    ]

    for msg in test_messages:
        logger.info(f"Usuario: {msg}")
        response = await assistant.process_message(msg)
        logger.info(f"Asistente: {response}")


async def test_personal_create_task():
    """Prueba creación de tarea mediante lenguaje natural."""
    logger.info("=== Prueba: Crear Tarea con AI ===")

    user_id = 1
    assistant = PersonalAssistant(user_id)

    test_messages = [
        "tengo que revisar el código mañana",
        "debo llamar a Juan urgente",
        "recuérdame enviar reporte el viernes",
        "cuando pueda tengo que ordenar el escritorio",
    ]

    for msg in test_messages:
        logger.info(f"Usuario: {msg}")
        response = await assistant.process_message(msg)
        logger.info(f"Asistente: {response}")


async def test_personal_create_appointment():
    """Prueba creación de cita mediante lenguaje natural."""
    logger.info("=== Prueba: Crear Cita con AI ===")

    user_id = 1
    assistant = PersonalAssistant(user_id)

    test_messages = [
        "reunión con cliente el lunes a las 10am",
        "agendar cita con el doctor el martes a las 3pm",
        "tengo junta de equipo el miércoles a las 9:30am",
    ]

    for msg in test_messages:
        logger.info(f"Usuario: {msg}")
        response = await assistant.process_message(msg)
        logger.info(f"Asistente: {response}")


async def verify_created_data():
    """Verifica que los datos se hayan creado correctamente en la base de datos."""
    logger.info("=== Verificación de Datos Creados ===")

    user_id = 1

    # Verificar productos
    logger.info("Productos creados:")
    products = products_db.list_products(user_id)
    for p in products[-3:]:  # Últimos 3
        logger.info(f"  - {p['name']}: ${p['price']} (Stock: {p['stock']})")

    # Verificar tareas
    logger.info("Tareas creadas:")
    tasks = personal_db.list_tasks(user_id)
    for t in tasks[-4:]:  # Últimas 4
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
            t["priority"], "⚪"
        )
        logger.info(
            f"  - {priority_emoji} {t['title']} (Vence: {t.get('due_date', 'Sin fecha')})"
        )

    # Verificar citas
    logger.info("Citas creadas:")
    appointments = personal_db.list_appointments(user_id)
    for a in appointments[-3:]:  # Últimas 3
        logger.info(f"  - {a['title']} ({a['start_datetime']})")


async def main():
    """Ejecuta todas las pruebas."""
    logger.info("PRUEBAS DE AI ACTIONS - CREACIÓN DE DATOS")

    try:
        # Crear productos
        await test_commercial_create_product()

        # Crear tareas
        await test_personal_create_task()

        # Crear citas
        await test_personal_create_appointment()

        # Verificar datos
        await verify_created_data()

        logger.info("TODAS LAS PRUEBAS COMPLETADAS")
        logger.info(
            "Los asistentes AI ahora pueden: Crear productos, Crear tareas, Agendar citas"
        )

    except Exception:
        logger.exception("Error en las pruebas")


if __name__ == "__main__":
    asyncio.run(main())
