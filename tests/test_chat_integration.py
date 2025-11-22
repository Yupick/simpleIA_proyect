"""
Test de integración del chat con LLM y AI Actions.
"""
import sys
from pathlib import Path

# Agregar el directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.models import model_manager
from app.assistants.personal import PersonalAssistant
from app.assistants.commercial import CommercialAssistant


def test_model_manager_load():
    """Verificar que el model_manager carga correctamente."""
    print("=" * 60)
    print("TEST 1: Verificar carga de model_manager")
    print("=" * 60)
    
    # Cargar modelo
    model_manager.load_model(force=True)
    
    print(f"✓ Provider instance: {model_manager._provider_instance}")
    print(f"✓ Current model: {model_manager._current_model_name}")
    print(f"✓ Provider type: {type(model_manager._provider_instance).__name__}")
    
    assert model_manager._provider_instance is not None, "Provider no cargado"
    print("\n✅ Model Manager cargado correctamente\n")


def test_intent_parser():
    """Verificar que IntentParser detecta intenciones."""
    print("=" * 60)
    print("TEST 2: Verificar IntentParser (AI Actions)")
    print("=" * 60)
    
    from app.assistants.actions import IntentParser
    
    # Test crear tarea
    intent, params = IntentParser.detect_intent("Recuérdame llamar a Juan mañana a las 3pm")
    print(f"Mensaje: 'Recuérdame llamar a Juan mañana a las 3pm'")
    print(f"✓ Intent detectado: {intent}")
    print(f"✓ Parámetros: {params}")
    assert intent == "create_task", f"Esperado 'create_task', obtenido '{intent}'"
    
    # Test crear cita
    intent, params = IntentParser.detect_intent("Tengo reunión con el cliente el lunes a las 10am")
    print(f"\nMensaje: 'Tengo reunión con el cliente el lunes a las 10am'")
    print(f"✓ Intent detectado: {intent}")
    print(f"✓ Parámetros: {params}")
    assert intent == "create_appointment", f"Esperado 'create_appointment', obtenido '{intent}'"
    
    # Test crear producto
    intent, params = IntentParser.detect_intent("Agrega laptop Dell por $1500")
    print(f"\nMensaje: 'Agrega laptop Dell por $1500'")
    print(f"✓ Intent detectado: {intent}")
    print(f"✓ Parámetros: {params}")
    assert intent == "create_product", f"Esperado 'create_product', obtenido '{intent}'"
    
    print("\n✅ IntentParser funciona correctamente\n")


async def test_assistant_with_llm():
    """Verificar que los asistentes usan el LLM."""
    print("=" * 60)
    print("TEST 3: Verificar Assistant + LLM")
    print("=" * 60)
    
    # Crear asistente personal para usuario de prueba
    assistant = PersonalAssistant(user_id=999)
    
    # Test 1: Consulta simple (usa LLM)
    print("\n--- Test 3.1: Consulta simple ---")
    message = "¿Qué tareas tengo pendientes?"
    print(f"Mensaje: '{message}'")
    
    response = await assistant.process_message(
        message=message,
        conversation_history=[],
        llm_provider=model_manager._provider_instance
    )
    
    print(f"✓ Respuesta del asistente:\n{response}")
    assert len(response) > 0, "Respuesta vacía"
    assert "[ERROR]" not in response, f"Error en LLM: {response}"
    
    # Test 2: Crear tarea con AI Actions
    print("\n--- Test 3.2: Crear tarea (AI Actions) ---")
    message = "Recuérdame revisar el reporte mañana a las 3pm"
    print(f"Mensaje: '{message}'")
    
    response = await assistant.process_message(
        message=message,
        conversation_history=[],
        llm_provider=model_manager._provider_instance
    )
    
    print(f"✓ Respuesta del asistente:\n{response}")
    assert len(response) > 0, "Respuesta vacía"
    # Debería contener confirmación de creación
    assert any(word in response.lower() for word in ['tarea', 'creada', 'agregada', 'recordatorio']), \
        f"Respuesta no indica creación: {response}"
    
    print("\n✅ Assistant + LLM funcionan correctamente\n")


if __name__ == "__main__":
    import asyncio
    
    print("\n" + "="*60)
    print("SUITE DE TESTS: Integración Chat + LLM + AI Actions")
    print("="*60 + "\n")
    
    try:
        # Test 1: Model Manager
        test_model_manager_load()
        
        # Test 2: Intent Parser
        test_intent_parser()
        
        # Test 3: Assistant con LLM
        asyncio.run(test_assistant_with_llm())
        
        print("="*60)
        print("✅ TODOS LOS TESTS PASARON EXITOSAMENTE")
        print("="*60)
        print("\n🎉 El sistema está listo para:")
        print("   - Usar LLM para generar respuestas")
        print("   - Detectar intenciones (crear tarea/cita/producto)")
        print("   - Ejecutar acciones automáticamente")
        print("   - Mantener datos aislados por usuario")
        print()
        
    except Exception as e:
        print(f"\n❌ ERROR EN TEST: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
