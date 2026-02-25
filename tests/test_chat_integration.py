"""
Test de integración del chat con LLM y AI Actions.
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import logging  # noqa: E402

from app.models import model_manager  # noqa: E402
from app.assistants.personal import PersonalAssistant  # noqa: E402

logger = logging.getLogger(__name__)


def test_model_manager_load():
    """Verificar que el model_manager carga correctamente."""
    logger.info("TEST 1: Verificar carga de model_manager")
    # Cargar modelo
    model_manager.load_model(force=True)
    logger.info(f"Provider instance: {model_manager._provider_instance}")
    logger.info(f"Current model: {model_manager._current_model_name}")
    logger.info(f"Provider type: {type(model_manager._provider_instance).__name__}")
    assert model_manager._provider_instance is not None, "Provider no cargado"
    logger.info("Model Manager cargado correctamente")


def test_intent_parser():
    """Verificar que IntentParser detecta intenciones."""
    logger.info("TEST 2: Verificar IntentParser (AI Actions)")
    from app.assistants.actions import IntentParser

    # Test crear tarea
    intent, params = IntentParser.detect_intent(
        "Recuérdame llamar a Juan mañana a las 3pm"
    )
    logger.info("Mensaje: 'Recuérdame llamar a Juan mañana a las 3pm'")
    logger.info(f"Intent detectado: {intent}")
    logger.info(f"Parámetros: {params}")
    assert intent == "create_task", f"Esperado 'create_task', obtenido '{intent}'"
    # Test crear cita
    intent, params = IntentParser.detect_intent(
        "Tengo reunión con el cliente el lunes a las 10am"
    )
    logger.info("Mensaje: 'Tengo reunión con el cliente el lunes a las 10am'")
    logger.info(f"Intent detectado: {intent}")
    logger.info(f"Parámetros: {params}")
    assert (
        intent == "create_appointment"
    ), f"Esperado 'create_appointment', obtenido '{intent}'"
    # Test crear producto
    intent, params = IntentParser.detect_intent("Agrega laptop Dell por $1500")
    logger.info("Mensaje: 'Agrega laptop Dell por $1500'")
    logger.info(f"Intent detectado: {intent}")
    logger.info(f"Parámetros: {params}")
    assert intent == "create_product", f"Esperado 'create_product', obtenido '{intent}'"
    logger.info("IntentParser funciona correctamente")


async def test_assistant_with_llm():
    """Verificar que los asistentes usan el LLM."""
    logger.info("TEST 3: Verificar Assistant + LLM")
    # Crear asistente personal para usuario de prueba
    assistant = PersonalAssistant(user_id=999)
    # Test 1: Consulta simple (usa LLM)
    logger.info("Test 3.1: Consulta simple")
    message = "¿Qué tareas tengo pendientes?"
    logger.info(f"Mensaje: '{message}'")
    response = await assistant.process_message(
        message=message,
        conversation_history=[],
        llm_provider=model_manager._provider_instance,
    )
    logger.info(f"Respuesta del asistente: {response}")
    assert len(response) > 0, "Respuesta vacía"
    assert "[ERROR]" not in response, f"Error en LLM: {response}"
    # Test 2: Crear tarea con AI Actions
    logger.info("Test 3.2: Crear tarea (AI Actions)")
    message = "Recuérdame revisar el reporte mañana a las 3pm"
    logger.info(f"Mensaje: '{message}'")
    response = await assistant.process_message(
        message=message,
        conversation_history=[],
        llm_provider=model_manager._provider_instance,
    )
    logger.info(f"Respuesta del asistente: {response}")
    assert len(response) > 0, "Respuesta vacía"
    assert any(
        word in response.lower()
        for word in ["tarea", "creada", "agregada", "recordatorio"]
    ), f"Respuesta no indica creación: {response}"
    logger.info("Assistant + LLM funcionan correctamente")


if __name__ == "__main__":
    import asyncio

    try:
        test_model_manager_load()
        test_intent_parser()
        asyncio.run(test_assistant_with_llm())
        logger.info("TODOS LOS TESTS PASARON EXITOSAMENTE")
    except Exception:
        logger.exception("ERROR EN TEST")
        sys.exit(1)
