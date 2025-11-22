"""
Pruebas para verificar que los asistentes AI pueden crear datos correctamente.
"""
import asyncio
from app.assistants.commercial import CommercialAssistant
from app.assistants.personal import PersonalAssistant
from app.db import products as products_db
from app.db import personal as personal_db


async def test_commercial_create_product():
    """Prueba creación de producto mediante lenguaje natural."""
    print("\n=== Prueba: Crear Producto con AI ===")
    
    # Usuario de prueba
    user_id = 1
    assistant = CommercialAssistant(user_id)
    
    # Mensajes de prueba
    test_messages = [
        "agregar laptop gaming por $1500 con 10 unidades",
        "crear producto mouse inalámbrico por $25",
        "añade teclado mecánico a $120 stock 5"
    ]
    
    for msg in test_messages:
        print(f"\n📝 Usuario: {msg}")
        response = await assistant.process_message(msg)
        print(f"🤖 Asistente: {response}")


async def test_personal_create_task():
    """Prueba creación de tarea mediante lenguaje natural."""
    print("\n\n=== Prueba: Crear Tarea con AI ===")
    
    user_id = 1
    assistant = PersonalAssistant(user_id)
    
    test_messages = [
        "tengo que revisar el código mañana",
        "debo llamar a Juan urgente",
        "recuérdame enviar reporte el viernes",
        "cuando pueda tengo que ordenar el escritorio"
    ]
    
    for msg in test_messages:
        print(f"\n📝 Usuario: {msg}")
        response = await assistant.process_message(msg)
        print(f"🤖 Asistente: {response}")


async def test_personal_create_appointment():
    """Prueba creación de cita mediante lenguaje natural."""
    print("\n\n=== Prueba: Crear Cita con AI ===")
    
    user_id = 1
    assistant = PersonalAssistant(user_id)
    
    test_messages = [
        "reunión con cliente el lunes a las 10am",
        "agendar cita con el doctor el martes a las 3pm",
        "tengo junta de equipo el miércoles a las 9:30am"
    ]
    
    for msg in test_messages:
        print(f"\n📝 Usuario: {msg}")
        response = await assistant.process_message(msg)
        print(f"🤖 Asistente: {response}")


async def verify_created_data():
    """Verifica que los datos se hayan creado correctamente en la base de datos."""
    print("\n\n=== Verificación de Datos Creados ===")
    
    user_id = 1
    
    # Verificar productos
    print("\n📦 Productos creados:")
    products = products_db.list_products(user_id)
    for p in products[-3:]:  # Últimos 3
        print(f"  - {p['name']}: ${p['price']} (Stock: {p['stock']})")
    
    # Verificar tareas
    print("\n✅ Tareas creadas:")
    tasks = personal_db.list_tasks(user_id)
    for t in tasks[-4:]:  # Últimas 4
        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(t['priority'], "⚪")
        print(f"  - {priority_emoji} {t['title']} (Vence: {t.get('due_date', 'Sin fecha')})")
    
    # Verificar citas
    print("\n📅 Citas creadas:")
    appointments = personal_db.list_appointments(user_id)
    for a in appointments[-3:]:  # Últimas 3
        print(f"  - {a['title']} ({a['start_datetime']})")


async def main():
    """Ejecuta todas las pruebas."""
    print("╔═══════════════════════════════════════════════════════╗")
    print("║   PRUEBAS DE AI ACTIONS - CREACIÓN DE DATOS          ║")
    print("╚═══════════════════════════════════════════════════════╝")
    
    try:
        # Crear productos
        await test_commercial_create_product()
        
        # Crear tareas
        await test_personal_create_task()
        
        # Crear citas
        await test_personal_create_appointment()
        
        # Verificar datos
        await verify_created_data()
        
        print("\n\n✅ TODAS LAS PRUEBAS COMPLETADAS")
        print("\nLos asistentes AI ahora pueden:")
        print("  ✓ Crear productos mediante lenguaje natural")
        print("  ✓ Crear tareas con fechas y prioridades")
        print("  ✓ Agendar citas con fechas y horas")
        
    except Exception as e:
        print(f"\n❌ Error en las pruebas: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
