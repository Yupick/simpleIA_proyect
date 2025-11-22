"""
Tests de integración para el Módulo 4.
Prueba todo el flujo multi-tenant con asistentes contextuales.
"""
import pytest
import sys
from pathlib import Path

# Agregar el directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.db import products, personal, conversations
from app.db.sqlite import create_user, get_user, init_user_db, list_users_with_roles
from app.assistants.commercial import CommercialAssistant
from app.assistants.personal import PersonalAssistant
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TestM4MultiTenant:
    """Tests de aislamiento multi-tenant."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup para cada test."""
        # Inicializar DBs
        init_user_db()
        products.init_products_db()
        personal.init_personal_db()
        conversations.init_conversations_db()
        
        # Crear usuarios de prueba
        self.user1_id = self._create_test_user("test_user1", "user")
        self.user2_id = self._create_test_user("test_user2", "user")
        self.admin_id = self._create_test_user("test_admin", "superadmin")
    
    def _create_test_user(self, username: str, role: str) -> int:
        """Crea un usuario de prueba y retorna su ID."""
        # Verificar si ya existe
        existing = get_user(username)
        if existing:
            return existing['id']
        
        # Crear nuevo
        is_admin = (role == "superadmin")
        hashed_pwd = pwd_context.hash("test123")
        create_user(username, hashed_pwd, is_admin, role)
        
        user = get_user(username)
        return user['id']
    
    def test_user_isolation_products(self):
        """Verifica que cada usuario solo vea sus propios productos."""
        # User1 crea productos
        p1_id = products.create_product(
            user_id=self.user1_id,
            name="Laptop User1",
            price=1000.0,
            stock=5
        )
        
        p2_id = products.create_product(
            user_id=self.user1_id,
            name="Mouse User1",
            price=50.0,
            stock=10
        )
        
        # User2 crea productos
        p3_id = products.create_product(
            user_id=self.user2_id,
            name="Laptop User2",
            price=1500.0,
            stock=3
        )
        
        # Verificar aislamiento
        user1_products = products.list_products(self.user1_id)
        user2_products = products.list_products(self.user2_id)
        
        assert len(user1_products) == 2, "User1 debe tener 2 productos"
        assert len(user2_products) == 1, "User2 debe tener 1 producto"
        
        # User1 no puede acceder a productos de User2
        assert products.get_product(p3_id, self.user1_id) is None
        
        # User2 no puede acceder a productos de User1
        assert products.get_product(p1_id, self.user2_id) is None
        
        print("✅ Test aislamiento de productos: PASSED")
    
    def test_user_isolation_tasks(self):
        """Verifica que cada usuario solo vea sus propias tareas."""
        # User1 crea tareas
        t1_id = personal.create_task(
            user_id=self.user1_id,
            title="Tarea User1",
            priority="high"
        )
        
        # User2 crea tareas
        t2_id = personal.create_task(
            user_id=self.user2_id,
            title="Tarea User2",
            priority="medium"
        )
        
        # Verificar aislamiento
        user1_tasks = personal.list_tasks(self.user1_id)
        user2_tasks = personal.list_tasks(self.user2_id)
        
        assert len(user1_tasks) == 1
        assert len(user2_tasks) == 1
        
        # Verificar que no puede acceder a tareas de otro usuario
        assert personal.get_task(t2_id, self.user1_id) is None
        assert personal.get_task(t1_id, self.user2_id) is None
        
        print("✅ Test aislamiento de tareas: PASSED")
    
    def test_user_isolation_appointments(self):
        """Verifica que cada usuario solo vea sus propias citas."""
        # User1 crea cita
        a1_id = personal.create_appointment(
            user_id=self.user1_id,
            title="Reunión User1",
            start_datetime="2025-11-22 10:00:00"
        )
        
        # User2 crea cita
        a2_id = personal.create_appointment(
            user_id=self.user2_id,
            title="Reunión User2",
            start_datetime="2025-11-22 15:00:00"
        )
        
        # Verificar aislamiento
        user1_apts = personal.list_appointments(self.user1_id)
        user2_apts = personal.list_appointments(self.user2_id)
        
        assert len(user1_apts) == 1
        assert len(user2_apts) == 1
        
        assert personal.get_appointment(a2_id, self.user1_id) is None
        assert personal.get_appointment(a1_id, self.user2_id) is None
        
        print("✅ Test aislamiento de citas: PASSED")
    
    def test_user_isolation_conversations(self):
        """Verifica que cada usuario solo vea sus propias conversaciones."""
        # User1 crea conversación
        c1_id = conversations.create_conversation(self.user1_id, "commercial")
        conversations.add_message(c1_id, "user", "Hola desde User1")
        
        # User2 crea conversación
        c2_id = conversations.create_conversation(self.user2_id, "personal")
        conversations.add_message(c2_id, "user", "Hola desde User2")
        
        # Verificar aislamiento
        user1_convs = conversations.list_conversations(self.user1_id)
        user2_convs = conversations.list_conversations(self.user2_id)
        
        assert len(user1_convs) == 1
        assert len(user2_convs) == 1
        
        assert conversations.get_conversation(c2_id, self.user1_id) is None
        assert conversations.get_conversation(c1_id, self.user2_id) is None
        
        print("✅ Test aislamiento de conversaciones: PASSED")


class TestCommercialAssistant:
    """Tests del asistente comercial."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup para cada test."""
        init_user_db()
        products.init_products_db()
        
        # Crear usuario de prueba
        user = get_user("commercial_test")
        if not user:
            hashed_pwd = pwd_context.hash("test123")
            create_user("commercial_test", hashed_pwd, False, "user")
            user = get_user("commercial_test")
        
        self.user_id = user['id']
        self.assistant = CommercialAssistant(user_id=self.user_id)
        
        # Crear productos de prueba
        self._create_sample_products()
    
    def _create_sample_products(self):
        """Crea productos de ejemplo."""
        products.create_product(
            user_id=self.user_id,
            name="Laptop HP",
            description="Laptop HP con 16GB RAM",
            price=1200.0,
            sku="LAP-HP-001",
            category="Computadoras",
            stock=5
        )
        
        products.create_product(
            user_id=self.user_id,
            name="Mouse Logitech",
            description="Mouse inalámbrico",
            price=45.0,
            sku="MOU-LOG-001",
            category="Accesorios",
            stock=20
        )
        
        products.create_product(
            user_id=self.user_id,
            name="Teclado Mecánico",
            description="Teclado gaming RGB",
            price=150.0,
            sku="TEC-MEC-001",
            category="Accesorios",
            stock=10
        )
    
    def test_get_context(self):
        """Verifica que el asistente obtenga el contexto correcto."""
        context = self.assistant.get_context()
        
        assert context['product_count'] == 3
        assert 'Computadoras' in context['categories']
        assert 'Accesorios' in context['categories']
        assert len(context['products']) == 3
        
        print("✅ Test context del asistente comercial: PASSED")
    
    def test_search_products(self):
        """Verifica la búsqueda de productos."""
        # Búsqueda por nombre
        results = self.assistant.search_relevant_products("laptop")
        assert len(results) > 0
        assert any("Laptop" in p['name'] for p in results)
        
        # Búsqueda por categoría
        results = self.assistant.search_relevant_products("accesorios")
        assert len(results) == 2
        
        print("✅ Test búsqueda de productos: PASSED")
    
    def test_build_system_prompt(self):
        """Verifica que el prompt del sistema se construya correctamente."""
        prompt = self.assistant.build_system_prompt()
        
        assert "asistente comercial" in prompt.lower()
        assert "3" in prompt  # Debe mencionar 3 productos
        assert "Laptop HP" in prompt
        assert "Mouse Logitech" in prompt
        
        print("✅ Test system prompt comercial: PASSED")


class TestPersonalAssistant:
    """Tests del asistente personal."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup para cada test."""
        init_user_db()
        personal.init_personal_db()
        
        # Crear usuario de prueba
        user = get_user("personal_test")
        if not user:
            hashed_pwd = pwd_context.hash("test123")
            create_user("personal_test", hashed_pwd, False, "user")
            user = get_user("personal_test")
        
        self.user_id = user['id']
        self.assistant = PersonalAssistant(user_id=self.user_id)
        
        # Crear datos de prueba
        self._create_sample_data()
    
    def _create_sample_data(self):
        """Crea citas y tareas de ejemplo."""
        # Citas
        personal.create_appointment(
            user_id=self.user_id,
            title="Reunión con cliente",
            start_datetime="2025-11-25 10:00:00",
            location="Oficina principal"
        )
        
        personal.create_appointment(
            user_id=self.user_id,
            title="Llamada de seguimiento",
            start_datetime="2025-11-26 15:00:00"
        )
        
        # Tareas
        personal.create_task(
            user_id=self.user_id,
            title="Preparar presentación",
            priority="high",
            due_date="2025-11-23"
        )
        
        personal.create_task(
            user_id=self.user_id,
            title="Revisar emails",
            priority="medium"
        )
    
    def test_get_context(self):
        """Verifica que el asistente obtenga el contexto correcto."""
        context = self.assistant.get_context()
        
        assert context['appointments_count'] == 2
        assert context['tasks_count'] == 2
        assert len(context['upcoming_appointments']) == 2
        assert len(context['pending_tasks']) == 2
        
        print("✅ Test context del asistente personal: PASSED")
    
    def test_get_pending_tasks_by_priority(self):
        """Verifica la agrupación de tareas por prioridad."""
        grouped = self.assistant.get_pending_tasks_by_priority()
        
        assert len(grouped['high']) == 1
        assert len(grouped['medium']) == 1
        assert len(grouped['low']) == 0
        
        print("✅ Test tareas por prioridad: PASSED")
    
    def test_build_system_prompt(self):
        """Verifica que el prompt del sistema se construya correctamente."""
        prompt = self.assistant.build_system_prompt()
        
        assert "asistente personal" in prompt.lower()
        assert "2" in prompt  # Menciona 2 citas
        assert "Reunión con cliente" in prompt
        assert "Preparar presentación" in prompt
        
        print("✅ Test system prompt personal: PASSED")


class TestDatabaseOperations:
    """Tests de operaciones CRUD."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup para cada test."""
        init_user_db()
        products.init_products_db()
        personal.init_personal_db()
        
        user = get_user("crud_test")
        if not user:
            hashed_pwd = pwd_context.hash("test123")
            create_user("crud_test", hashed_pwd, False, "user")
            user = get_user("crud_test")
        
        self.user_id = user['id']
    
    def test_product_crud(self):
        """Test completo de CRUD de productos."""
        # CREATE
        product_id = products.create_product(
            user_id=self.user_id,
            name="Test Product",
            price=100.0,
            stock=5
        )
        assert product_id is not None
        
        # READ
        product = products.get_product(product_id, self.user_id)
        assert product is not None
        assert product['name'] == "Test Product"
        assert product['price'] == 100.0
        
        # UPDATE
        success = products.update_product(
            product_id=product_id,
            user_id=self.user_id,
            name="Updated Product",
            price=150.0
        )
        assert success is True
        
        updated = products.get_product(product_id, self.user_id)
        assert updated['name'] == "Updated Product"
        assert updated['price'] == 150.0
        
        # DELETE (soft)
        success = products.delete_product(product_id, self.user_id)
        assert success is True
        
        deleted = products.get_product(product_id, self.user_id)
        assert deleted is None  # No visible porque active=0
        
        print("✅ Test CRUD productos: PASSED")
    
    def test_task_crud(self):
        """Test completo de CRUD de tareas."""
        # CREATE
        task_id = personal.create_task(
            user_id=self.user_id,
            title="Test Task",
            priority="high",
            due_date="2025-11-30"
        )
        assert task_id is not None
        
        # READ
        task = personal.get_task(task_id, self.user_id)
        assert task is not None
        assert task['title'] == "Test Task"
        assert task['priority'] == "high"
        
        # UPDATE
        success = personal.update_task(
            task_id=task_id,
            user_id=self.user_id,
            status="completed"
        )
        assert success is True
        
        updated = personal.get_task(task_id, self.user_id)
        assert updated['status'] == "completed"
        assert updated['completed_at'] is not None
        
        # DELETE
        success = personal.delete_task(task_id, self.user_id)
        assert success is True
        
        deleted = personal.get_task(task_id, self.user_id)
        assert deleted is None
        
        print("✅ Test CRUD tareas: PASSED")


if __name__ == "__main__":
    print("=" * 60)
    print("INICIANDO PRUEBAS DEL MÓDULO 4")
    print("=" * 60)
    print()
    
    # Ejecutar tests
    pytest.main([__file__, "-v", "-s"])
