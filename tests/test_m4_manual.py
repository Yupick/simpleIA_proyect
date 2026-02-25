"""
Tests manuales del Módulo 4 sin dependencias externas.
"""

# ruff: noqa: E402

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import logging  # noqa: E402
from passlib.context import CryptContext

from app.db import products, personal, conversations  # noqa: E402
from app.db.sqlite import create_user, get_user, init_user_db  # noqa: E402
from app.assistants.commercial import CommercialAssistant  # noqa: E402
from app.assistants.personal import PersonalAssistant  # noqa: E402

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def print_header(title):
    """Imprime un encabezado."""
    logger.info("\n%s", "=" * 70)
    logger.info("  %s", title)
    logger.info("%s\n", "=" * 70)


def print_test(name, passed):
    """Imprime el resultado de un test."""
    status = "✅ PASSED" if passed else "❌ FAILED"
    if passed:
        logger.info("%s - %s", status, name)
    else:
        logger.error("%s - %s", status, name)


class TestRunner:
    """Ejecutor de tests manual."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.user1_id = None
        self.user2_id = None

    def setup_users(self):
        """Crea usuarios de prueba."""
        logger.info("Configurando usuarios de prueba...")
        init_user_db()

        # User1
        user1 = get_user("test_user1")
        if not user1:
            create_user("test_user1", pwd_context.hash("test123"), False, "user")
            user1 = get_user("test_user1")
        self.user1_id = user1["id"]
        logger.info("  ✓ User1 ID: %s", self.user1_id)

        # User2
        user2 = get_user("test_user2")
        if not user2:
            create_user("test_user2", pwd_context.hash("test123"), False, "user")
            user2 = get_user("test_user2")
        self.user2_id = user2["id"]
        logger.info("  ✓ User2 ID: %s", self.user2_id)

    def run_test(self, test_func, name):
        """Ejecuta un test y registra el resultado."""
        try:
            test_func()
            print_test(name, True)
            self.passed += 1
        except AssertionError as e:
            print_test(name, False)
            logger.error("    Error: %s", e)
            self.failed += 1
        except Exception as e:
            print_test(name, False)
            logger.exception("    Exception: %s", e)
            self.failed += 1

    def print_summary(self):
        """Imprime resumen final."""
        print_header("RESUMEN DE PRUEBAS")
        total = self.passed + self.failed
        logger.info("Total de tests: %s", total)
        logger.info("✅ Passed: %s", self.passed)
        logger.info("❌ Failed: %s", self.failed)

        if self.failed == 0:
            logger.info("\n🎉 ¡TODAS LAS PRUEBAS PASARON!")
        else:
            logger.warning("\n⚠️  %s prueba(s) fallaron", self.failed)
        logger.info("")


def test_product_isolation(runner):
    """Test: Aislamiento de productos entre usuarios."""
    # Inicializar DB
    products.init_products_db()

    # User1 crea productos
    p1 = products.create_product(
        user_id=runner.user1_id, name="Laptop User1", price=1000.0, stock=5
    )

    products.create_product(
        user_id=runner.user1_id, name="Mouse User1", price=50.0, stock=10
    )

    # User2 crea producto
    p3 = products.create_product(
        user_id=runner.user2_id, name="Laptop User2", price=1500.0, stock=3
    )

    # Verificar aislamiento
    user1_products = products.list_products(runner.user1_id)
    user2_products = products.list_products(runner.user2_id)

    assert (
        len(user1_products) >= 2
    ), f"User1 debe tener al menos 2 productos, tiene {len(user1_products)}"
    assert (
        len(user2_products) >= 1
    ), f"User2 debe tener al menos 1 producto, tiene {len(user2_products)}"

    # User1 no puede ver productos de User2
    user2_product_from_user1 = products.get_product(p3, runner.user1_id)
    assert (
        user2_product_from_user1 is None
    ), "User1 NO debe poder ver productos de User2"

    # User2 no puede ver productos de User1
    user1_product_from_user2 = products.get_product(p1, runner.user2_id)
    assert (
        user1_product_from_user2 is None
    ), "User2 NO debe poder ver productos de User1"

    logger.info("    User1 tiene %s productos", len(user1_products))
    logger.info("    User2 tiene %s productos", len(user2_products))
    logger.info("    ✓ Aislamiento verificado correctamente")


def test_task_isolation(runner):
    """Test: Aislamiento de tareas entre usuarios."""
    personal.init_personal_db()

    # User1 crea tarea
    t1 = personal.create_task(
        user_id=runner.user1_id, title="Tarea User1", priority="high"
    )

    # User2 crea tarea
    t2 = personal.create_task(
        user_id=runner.user2_id, title="Tarea User2", priority="medium"
    )

    # Verificar aislamiento
    user1_tasks = personal.list_tasks(runner.user1_id)
    user2_tasks = personal.list_tasks(runner.user2_id)

    assert len(user1_tasks) >= 1, "User1 debe tener al menos 1 tarea"
    assert len(user2_tasks) >= 1, "User2 debe tener al menos 1 tarea"

    # Verificar que no pueden acceder a tareas del otro
    assert personal.get_task(t2, runner.user1_id) is None
    assert personal.get_task(t1, runner.user2_id) is None

    logger.info("    User1 tiene %s tareas", len(user1_tasks))
    logger.info("    User2 tiene %s tareas", len(user2_tasks))


def test_appointment_isolation(runner):
    """Test: Aislamiento de citas entre usuarios."""
    personal.init_personal_db()

    # User1 crea cita
    a1 = personal.create_appointment(
        user_id=runner.user1_id,
        title="Reunión User1",
        start_datetime="2025-11-25 10:00:00",
    )

    # User2 crea cita
    a2 = personal.create_appointment(
        user_id=runner.user2_id,
        title="Reunión User2",
        start_datetime="2025-11-25 15:00:00",
    )

    # Verificar aislamiento
    user1_apts = personal.list_appointments(runner.user1_id)
    user2_apts = personal.list_appointments(runner.user2_id)

    assert len(user1_apts) >= 1
    assert len(user2_apts) >= 1

    assert personal.get_appointment(a2, runner.user1_id) is None
    assert personal.get_appointment(a1, runner.user2_id) is None

    logger.info("    User1 tiene %s citas", len(user1_apts))
    logger.info("    User2 tiene %s citas", len(user2_apts))


def test_conversation_isolation(runner):
    """Test: Aislamiento de conversaciones entre usuarios."""
    conversations.init_conversations_db()

    # User1 crea conversación
    c1 = conversations.create_conversation(runner.user1_id, "commercial")
    conversations.add_message(c1, "user", "Hola desde User1")

    # User2 crea conversación
    c2 = conversations.create_conversation(runner.user2_id, "personal")
    conversations.add_message(c2, "user", "Hola desde User2")

    # Verificar aislamiento
    user1_convs = conversations.list_conversations(runner.user1_id)
    user2_convs = conversations.list_conversations(runner.user2_id)

    assert len(user1_convs) >= 1
    assert len(user2_convs) >= 1

    assert conversations.get_conversation(c2, runner.user1_id) is None
    assert conversations.get_conversation(c1, runner.user2_id) is None

    logger.info("    User1 tiene %s conversaciones", len(user1_convs))
    logger.info("    User2 tiene %s conversaciones", len(user2_convs))


def test_commercial_assistant(runner):
    """Test: Asistente comercial."""
    products.init_products_db()

    # Crear productos para el test
    products.create_product(
        user_id=runner.user1_id,
        name="Laptop HP Gaming",
        description="Laptop potente para gaming",
        price=1500.0,
        sku="LAP-HP-001",
        category="Computadoras",
        stock=3,
    )

    products.create_product(
        user_id=runner.user1_id,
        name="Mouse Logitech G502",
        description="Mouse gaming de alta precisión",
        price=80.0,
        sku="MOU-LOG-001",
        category="Accesorios",
        stock=15,
    )

    # Crear asistente
    assistant = CommercialAssistant(user_id=runner.user1_id)

    # Test: Get context
    context = assistant.get_context()
    assert context["product_count"] >= 2
    assert len(context["categories"]) > 0

    logger.info(
        "    ✓ Context: %s productos, %s categorías",
        context["product_count"],
        len(context["categories"]),
    )

    # Test: Search products
    results = assistant.search_relevant_products("laptop")
    assert len(results) > 0
    assert any("Laptop" in p["name"] for p in results)

    logger.info("    ✓ Búsqueda 'laptop': %s resultados", len(results))

    # Test: System prompt
    prompt = assistant.build_system_prompt()
    assert "asistente comercial" in prompt.lower()
    assert len(prompt) > 100

    logger.info("    ✓ System prompt: %s caracteres", len(prompt))


def test_personal_assistant(runner):
    """Test: Asistente personal."""
    personal.init_personal_db()

    # Crear datos de prueba
    personal.create_appointment(
        user_id=runner.user1_id,
        title="Reunión importante",
        start_datetime="2025-11-26 10:00:00",
        location="Sala de juntas",
    )

    personal.create_task(
        user_id=runner.user1_id,
        title="Preparar presentación",
        priority="high",
        due_date="2025-11-24",
    )

    # Crear asistente
    assistant = PersonalAssistant(user_id=runner.user1_id)

    # Test: Get context
    context = assistant.get_context()
    assert context["appointments_count"] >= 1
    assert context["tasks_count"] >= 1

    logger.info(
        "    ✓ Context: %s citas, %s tareas",
        context["appointments_count"],
        context["tasks_count"],
    )

    # Test: Get pending tasks by priority
    grouped = assistant.get_pending_tasks_by_priority()
    assert "high" in grouped
    assert "medium" in grouped
    assert "low" in grouped

    logger.info(
        "    ✓ Tareas por prioridad: High=%s, Med=%s, Low=%s",
        len(grouped["high"]),
        len(grouped["medium"]),
        len(grouped["low"]),
    )

    # Test: System prompt
    prompt = assistant.build_system_prompt()
    assert "asistente personal" in prompt.lower()
    assert len(prompt) > 100

    logger.info("    ✓ System prompt: %s caracteres", len(prompt))


def test_product_crud(runner):
    """Test: CRUD completo de productos."""
    products.init_products_db()

    # CREATE
    product_id = products.create_product(
        user_id=runner.user1_id, name="Test Product CRUD", price=100.0, stock=5
    )
    assert product_id is not None
    logger.info("    ✓ CREATE: Producto ID %s", product_id)

    # READ
    product = products.get_product(product_id, runner.user1_id)
    assert product is not None
    assert product["name"] == "Test Product CRUD"
    logger.info("    ✓ READ: %s", product["name"])

    # UPDATE
    success = products.update_product(
        product_id=product_id,
        user_id=runner.user1_id,
        name="Test Product UPDATED",
        price=150.0,
    )
    assert success is True

    updated = products.get_product(product_id, runner.user1_id)
    assert updated["name"] == "Test Product UPDATED"
    assert updated["price"] == 150.0
    logger.info("    ✓ UPDATE: %s - $%s", updated["name"], updated["price"])

    # DELETE (soft)
    success = products.delete_product(product_id, runner.user1_id)
    assert success is True

    # El producto sigue existiendo pero con active=False
    deleted = products.get_product(product_id, runner.user1_id)
    assert deleted is not None, "El producto debe existir después del soft delete"
    assert deleted["active"] is False, "El producto debe estar inactivo"
    logger.info("    ✓ DELETE: Producto marcado como inactivo (active=False)")

    # Verificar que no aparece en la lista de activos
    active_products = products.list_products(runner.user1_id, active_only=True)
    active_ids = [p["id"] for p in active_products]
    assert (
        product_id not in active_ids
    ), "Producto inactivo no debe aparecer en lista de activos"
    logger.info("    ✓ Producto no aparece en lista de activos")


def test_analytics(runner):
    """Test: Sistema de analytics."""
    conversations.init_conversations_db()

    # Crear conversación y mensajes
    conv_id = conversations.create_conversation(runner.user1_id, "commercial")
    conversations.add_message(conv_id, "user", "Hola")
    conversations.add_message(conv_id, "assistant", "Hola, ¿en qué puedo ayudarte?")
    conversations.add_message(conv_id, "user", "¿Tienes laptops?")

    # Track eventos
    conversations.track_event(runner.user1_id, "message_sent", "commercial")
    conversations.track_event(runner.user1_id, "product_query", "laptop")

    # Get stats
    stats = conversations.get_user_stats(runner.user1_id)
    assert stats["total_conversations"] >= 1
    assert stats["total_messages"] >= 3

    logger.info(
        "    ✓ Stats: %s conversaciones, %s mensajes",
        stats["total_conversations"],
        stats["total_messages"],
    )
    logger.info("    ✓ Eventos rastreados: %s", len(stats["events"]))


def main():
    """Función principal."""
    print_header("PRUEBAS DEL MÓDULO 4 - SISTEMA MULTI-TENANT")

    runner = TestRunner()

    # Setup
    logger.info("🔧 Inicializando entorno de pruebas...")
    runner.setup_users()

    # Tests de aislamiento multi-tenant
    print_header("TESTS DE AISLAMIENTO MULTI-TENANT")
    runner.run_test(lambda: test_product_isolation(runner), "Aislamiento de Productos")
    runner.run_test(lambda: test_task_isolation(runner), "Aislamiento de Tareas")
    runner.run_test(lambda: test_appointment_isolation(runner), "Aislamiento de Citas")
    runner.run_test(
        lambda: test_conversation_isolation(runner), "Aislamiento de Conversaciones"
    )

    # Tests de asistentes
    print_header("TESTS DE ASISTENTES INTELIGENTES")
    runner.run_test(lambda: test_commercial_assistant(runner), "Asistente Comercial")
    runner.run_test(lambda: test_personal_assistant(runner), "Asistente Personal")

    # Tests de operaciones CRUD
    print_header("TESTS DE OPERACIONES CRUD")
    runner.run_test(lambda: test_product_crud(runner), "CRUD de Productos")

    # Tests de analytics
    print_header("TESTS DE ANALYTICS")
    runner.run_test(lambda: test_analytics(runner), "Sistema de Analytics")

    # Resumen
    runner.print_summary()


if __name__ == "__main__":
    main()
