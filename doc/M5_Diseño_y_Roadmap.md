# M5 - Diseño y Roadmap: Consolidación y Nuevas Funcionalidades

**Fecha**: 24 de noviembre de 2025
**Milestone**: M5 - Integración Real, Analytics Avanzados y Optimización
**Estado**: 📋 EN DISEÑO

---

## 📋 Resumen Ejecutivo

### Estado Actual del Proyecto (Post-M4)

**✅ Completado (M1-M4):**
- ✅ Arquitectura modular completa
- ✅ 3 proveedores LLM (HuggingFace, Claude, OpenAI)
- ✅ Sistema de entrenamiento unificado
- ✅ Panel de administración web completo
- ✅ Sistema multi-tenant con aislamiento de datos
- ✅ Asistentes IA especializados (Comercial + Personal)
- ✅ Gestión de productos, tareas y citas
- ✅ Sistema de roles y permisos
- ✅ Autenticación por cookies HttpOnly
- ✅ Embeddings y búsqueda semántica (FAISS)
- ✅ Cache LRU y streaming SSE
- ✅ Métricas y estadísticas

**⚠️ Implementado Parcialmente (Requiere Mejoras):**
- ⚠️ Integración WhatsApp (solo webhook stub)
- ⚠️ Sistema de recordatorios (solo scheduler sin envío real)
- ⚠️ Búsqueda semántica en asistentes (keyword-based solamente)
- ⚠️ Panel de entrenamiento (UI básica)
- ⚠️ Analytics de conversaciones (datos guardados, UI limitada)

**❌ NO Implementado (Pendiente):**
- ❌ Búsqueda RAG con embeddings en asistentes
- ❌ Notificaciones email como alternativa
- ❌ Exportación de datos (CSV/PDF)
- ❌ API rate limiting por usuario
- ❌ Tests de integración completos
- ❌ Documentación de API (Swagger/OpenAPI)
- ❌ Modo multi-idioma (i18n)
- ❌ Webhooks personalizados
- ❌ Configuración de horarios de recordatorios
- ❌ Dashboard de analytics avanzado

---

## 🎯 Roadmap M5: Prioridades y Planificación

### Fase 1: CRÍTICA - Completar Funcionalidades Core (Prioridad ALTA)

#### Sprint 5.1: Integración WhatsApp Real ⚠️ CRÍTICO

**Problema Actual:**
- Router `/api/whatsapp/webhook` existe pero solo hace logging
- No hay conexión real con WhatsApp Business API
- `send_whatsapp_message()` es placeholder
- No hay mapeo phone ↔ user_id persistente

**Objetivos:**
1. Integrar con WhatsApp Business Cloud API (Meta)
2. Implementar autenticación webhook real
3. Sistema de envío de mensajes outbound
4. Almacenar mapeo phone → user_id en DB
5. Gestión de sesiones y estado de conexión

**Tareas Detalladas:**

**1.1. Base de Datos WhatsApp**
```sql
-- Nueva tabla para vincular teléfonos
CREATE TABLE whatsapp_connections (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    phone_number TEXT UNIQUE NOT NULL,
    display_name TEXT,
    connected_at TIMESTAMP,
    last_activity TIMESTAMP,
    status TEXT DEFAULT 'active',  -- active|disconnected
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Logs de mensajes WhatsApp
CREATE TABLE whatsapp_messages (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    phone_number TEXT NOT NULL,
    direction TEXT NOT NULL,  -- inbound|outbound
    message TEXT NOT NULL,
    conversation_id INTEGER,
    status TEXT DEFAULT 'sent',  -- sent|delivered|read|failed
    error TEXT,
    created_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
```

**Archivo**: `app/db/whatsapp.py` (nuevo, ~150 líneas)

**1.2. Cliente WhatsApp Business API**

```python
# app/integrations/whatsapp_client.py
import httpx
from typing import Optional, Dict

class WhatsAppClient:
    """Cliente para WhatsApp Business Cloud API."""

    def __init__(self, access_token: str, phone_number_id: str):
        self.access_token = access_token
        self.phone_number_id = phone_number_id
        self.api_url = "https://graph.facebook.com/v18.0"

    async def send_message(
        self,
        to: str,
        message: str,
        template: Optional[str] = None
    ) -> Dict:
        """Envía mensaje por WhatsApp."""
        # Implementación real con httpx
        pass

    async def verify_webhook(self, mode: str, token: str, challenge: str) -> bool:
        """Verifica webhook de WhatsApp."""
        pass

    async def mark_as_read(self, message_id: str):
        """Marca mensaje como leído."""
        pass
```

**Archivo**: `app/integrations/whatsapp_client.py` (nuevo, ~200 líneas)

**1.3. Actualizar Router WhatsApp**

```python
# app/api/routers/whatsapp.py (modificar)

from app.integrations.whatsapp_client import WhatsAppClient
from app.db.whatsapp import (
    save_whatsapp_message,
    get_user_by_phone,
    link_phone_to_user
)

@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    """
    Webhook real de WhatsApp Business API.
    Procesa mensajes entrantes y los enruta al asistente correcto.
    """
    body = await request.json()

    # Extraer datos del mensaje
    entry = body.get('entry', [])[0]
    changes = entry.get('changes', [])[0]
    value = changes.get('value', {})
    messages = value.get('messages', [])

    if not messages:
        return {"status": "no messages"}

    message_data = messages[0]
    from_number = message_data.get('from')
    message_text = message_data.get('text', {}).get('body', '')
    message_id = message_data.get('id')

    # 1. Identificar usuario
    user = await get_user_by_phone(from_number)
    if not user:
        # Usuario nuevo, enviar mensaje de registro
        await whatsapp_client.send_message(
            to=from_number,
            message="¡Hola! Para usar este servicio, regístrate en nuestro sitio web."
        )
        return {"status": "user not registered"}

    # 2. Guardar mensaje entrante
    await save_whatsapp_message(
        user_id=user['id'],
        phone_number=from_number,
        direction='inbound',
        message=message_text
    )

    # 3. Detectar intención y procesar
    intent = detect_intent(message_text)

    if intent == 'commercial':
        assistant = CommercialAssistant(user_id=user['id'])
        response = await assistant.process_message(
            message=message_text,
            llm_provider=get_llm_provider()
        )
    elif intent == 'personal':
        assistant = PersonalAssistant(user_id=user['id'])
        response = await assistant.process_message(
            message=message_text,
            llm_provider=get_llm_provider()
        )

    # 4. Enviar respuesta por WhatsApp
    await whatsapp_client.send_message(
        to=from_number,
        message=response
    )

    # 5. Guardar mensaje saliente
    await save_whatsapp_message(
        user_id=user['id'],
        phone_number=from_number,
        direction='outbound',
        message=response
    )

    # 6. Marcar como leído
    await whatsapp_client.mark_as_read(message_id)

    return {"status": "processed"}
```

**1.4. Configuración y Variables de Entorno**

```bash
# .env
WHATSAPP_ACCESS_TOKEN=your_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_id_here
WHATSAPP_VERIFY_TOKEN=your_verify_token_here
WHATSAPP_WEBHOOK_URL=https://your-domain.com/api/whatsapp/webhook
```

**Estimación**:
- DB: 50 líneas
- WhatsApp Client: 200 líneas
- Router actualizado: 150 líneas modificadas
- Tests: 100 líneas
- **Total**: ~500 líneas
- **Tiempo**: 3-4 días

---

#### Sprint 5.2: Sistema de Recordatorios Completo ⚠️ CRÍTICO

**Problema Actual:**
- `ReminderScheduler` existe y funciona
- `send_reminder()` solo hace logging
- No hay integración con WhatsApp ni Email
- No hay UI para configurar preferencias

**Objetivos:**
1. Conectar recordatorios con WhatsApp
2. Implementar envío de recordatorios por Email
3. UI para configurar preferencias de notificaciones
4. Persistir preferencias en DB
5. Dashboard de historial de recordatorios

**Tareas Detalladas:**

**2.1. Base de Datos Preferencias**

```sql
CREATE TABLE reminder_preferences (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE,
    email_enabled BOOLEAN DEFAULT TRUE,
    whatsapp_enabled BOOLEAN DEFAULT FALSE,
    browser_enabled BOOLEAN DEFAULT FALSE,
    task_reminder_minutes INTEGER DEFAULT 60,
    appointment_reminder_minutes INTEGER DEFAULT 15,
    quiet_hours_start TIME,
    quiet_hours_end TIME,
    timezone TEXT DEFAULT 'UTC',
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE reminder_history (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    reminder_type TEXT NOT NULL,  -- task|appointment
    target_id INTEGER NOT NULL,  -- ID de la tarea o cita
    title TEXT NOT NULL,
    channel TEXT NOT NULL,  -- email|whatsapp|browser
    status TEXT DEFAULT 'sent',  -- sent|failed|pending
    error TEXT,
    sent_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Archivo**: `app/db/reminders.py` (nuevo, ~120 líneas)

**2.2. Cliente de Email**

```python
# app/integrations/email_client.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailClient:
    """Cliente para envío de emails."""

    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html: bool = False
    ):
        """Envía un email."""
        msg = MIMEMultipart('alternative')
        msg['From'] = self.username
        msg['To'] = to
        msg['Subject'] = subject

        if html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
```

**Archivo**: `app/integrations/email_client.py` (nuevo, ~80 líneas)

**2.3. Actualizar ReminderScheduler**

```python
# app/core/reminders.py (modificar)

from app.integrations.whatsapp_client import WhatsAppClient
from app.integrations.email_client import EmailClient
from app.db.reminders import (
    get_user_preferences,
    save_reminder_history
)

class ReminderScheduler:
    def __init__(self):
        self.whatsapp_client = WhatsAppClient(...)
        self.email_client = EmailClient(...)

    async def send_reminder(
        self,
        user_id: int,
        reminder_type: str,
        title: str,
        details: str,
        target_id: int,
        **kwargs
    ):
        """Envía recordatorio por los canales configurados del usuario."""

        # Obtener preferencias
        prefs = await get_user_preferences(user_id)

        # Verificar quiet hours
        now = datetime.now()
        if prefs.get('quiet_hours_start') and prefs.get('quiet_hours_end'):
            if is_in_quiet_hours(now, prefs):
                logger.info(f"User {user_id} in quiet hours, delaying reminder")
                return

        message = f"🔔 {title}\n{details}"
        sent_channels = []

        # Enviar por WhatsApp si está habilitado
        if prefs.get('whatsapp_enabled'):
            try:
                phone = await get_user_phone(user_id)
                if phone:
                    await self.whatsapp_client.send_message(
                        to=phone,
                        message=message
                    )
                    sent_channels.append('whatsapp')
                    await save_reminder_history(
                        user_id=user_id,
                        reminder_type=reminder_type,
                        target_id=target_id,
                        title=title,
                        channel='whatsapp',
                        status='sent'
                    )
            except Exception as e:
                logger.error(f"Error sending WhatsApp reminder: {e}")
                await save_reminder_history(
                    user_id=user_id,
                    reminder_type=reminder_type,
                    target_id=target_id,
                    title=title,
                    channel='whatsapp',
                    status='failed',
                    error=str(e)
                )

        # Enviar por Email si está habilitado
        if prefs.get('email_enabled'):
            try:
                email = await get_user_email(user_id)
                if email:
                    await self.email_client.send_email(
                        to=email,
                        subject=f"Recordatorio: {title}",
                        body=message
                    )
                    sent_channels.append('email')
                    await save_reminder_history(
                        user_id=user_id,
                        reminder_type=reminder_type,
                        target_id=target_id,
                        title=title,
                        channel='email',
                        status='sent'
                    )
            except Exception as e:
                logger.error(f"Error sending email reminder: {e}")
                await save_reminder_history(
                    user_id=user_id,
                    reminder_type=reminder_type,
                    target_id=target_id,
                    title=title,
                    channel='email',
                    status='failed',
                    error=str(e)
                )

        logger.info(f"Reminder sent to user {user_id} via {sent_channels}")
```

**2.4. Endpoints de Preferencias**

```python
# app/api/routers/user/reminders.py (nuevo)

@router.get("/preferences")
async def get_reminder_preferences(
    current_user = Depends(get_current_regular_user)
):
    """Obtiene preferencias de recordatorios del usuario."""
    prefs = await get_user_preferences(current_user['id'])
    return prefs

@router.post("/preferences")
async def save_reminder_preferences(
    preferences: ReminderPreferences,
    current_user = Depends(get_current_regular_user)
):
    """Guarda preferencias de recordatorios."""
    await save_user_preferences(current_user['id'], preferences)
    return {"success": True}

@router.get("/history")
async def get_reminder_history(
    days: int = 7,
    current_user = Depends(get_current_regular_user)
):
    """Obtiene historial de recordatorios enviados."""
    history = await get_user_reminder_history(
        user_id=current_user['id'],
        days=days
    )
    return history
```

**2.5. UI de Preferencias (Ya existe en templates/user/reminders.html)**
- Conectar con endpoints reales
- Cargar preferencias al iniciar
- Actualizar historial en tiempo real

**Estimación**:
- DB: 60 líneas
- Email Client: 80 líneas
- ReminderScheduler actualizado: 100 líneas modificadas
- Router: 150 líneas
- **Total**: ~390 líneas
- **Tiempo**: 2-3 días

---

#### Sprint 5.3: RAG con Embeddings en Asistentes 🔥 ALTA PRIORIDAD

**Problema Actual:**
- Sistema de embeddings implementado (FAISS + sentence-transformers)
- Asistentes usan búsqueda por keywords solamente
- No hay integración entre embeddings y asistentes
- Búsqueda de productos muy básica

**Objetivos:**
1. Integrar búsqueda semántica en CommercialAssistant
2. Búsqueda semántica de tareas/citas en PersonalAssistant
3. RAG: Contexto relevante desde embeddings al LLM
4. Indexación automática de productos/tareas/citas

**Tareas Detalladas:**

**3.1. Actualizar CommercialAssistant con RAG**

```python
# app/assistants/commercial.py (modificar)

from app.models.embeddings import get_embedding_store

class CommercialAssistant(BaseAssistant):

    def __init__(self, user_id: int):
        super().__init__(user_id)
        self.embedding_store = get_embedding_store()
        self.index_key = f"products_user_{user_id}"

    def index_products(self):
        """Indexa todos los productos del usuario en el embedding store."""
        products = list_products(user_id=self.user_id, active_only=True)

        if not products:
            return

        # Crear textos para embeddings
        documents = []
        for p in products:
            doc = f"{p['name']} - {p['description']} - Categoría: {p['category']} - Precio: ${p['price']} - Stock: {p['stock']}"
            documents.append(doc)

        # Limpiar índice anterior del usuario
        self.embedding_store.clear_user_index(self.index_key)

        # Agregar documentos
        self.embedding_store.add_documents(
            documents=documents,
            metadata=[{"product_id": p['id'], "user_id": self.user_id} for p in products],
            index_key=self.index_key
        )

        logger.info(f"Indexed {len(products)} products for user {self.user_id}")

    def search_relevant_products_semantic(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Búsqueda semántica de productos usando embeddings.

        Args:
            query: Consulta del usuario
            limit: Número máximo de resultados

        Returns:
            Lista de productos relevantes con scores
        """
        # Buscar documentos similares
        results = self.embedding_store.search(
            query=query,
            top_k=limit,
            index_key=self.index_key
        )

        if not results:
            return []

        # Obtener IDs de productos
        product_ids = [r['metadata']['product_id'] for r in results]

        # Cargar productos completos
        products = []
        for pid in product_ids:
            product = get_product_by_id(self.user_id, pid)
            if product:
                products.append(product)

        return products

    async def process_message(
        self,
        message: str,
        conversation_history: Optional[List[Dict]] = None,
        llm_provider = None
    ) -> str:
        """
        Procesa un mensaje con RAG (Retrieval Augmented Generation).

        Flow:
        1. Buscar productos relevantes con embeddings
        2. Construir contexto RAG
        3. Generar prompt aumentado
        4. Consultar LLM con contexto
        """
        # 1. Búsqueda semántica
        relevant_products = self.search_relevant_products_semantic(
            query=message,
            limit=3
        )

        # 2. Construir contexto RAG
        rag_context = ""
        if relevant_products:
            rag_context = "\n\nPRODUCTOS RELEVANTES ENCONTRADOS:\n"
            for p in relevant_products:
                rag_context += f"- {p['name']}: {p['description']} (${p['price']}, Stock: {p['stock']})\n"

        # 3. System prompt con contexto ampliado
        system_prompt = self.build_system_prompt()

        # 4. Prompt del usuario con RAG
        user_prompt = message
        if rag_context:
            user_prompt = f"{rag_context}\n\nPregunta del cliente: {message}"

        # 5. Generar respuesta con LLM
        if llm_provider:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            response = await llm_provider.generate(messages)
            return response
        else:
            # Fallback sin LLM
            return f"Encontré {len(relevant_products)} productos relevantes para tu consulta."
```

**3.2. Actualizar PersonalAssistant con RAG**

```python
# app/assistants/personal.py (modificar)

class PersonalAssistant(BaseAssistant):

    def index_tasks_and_appointments(self):
        """Indexa tareas y citas del usuario."""
        tasks = list_tasks(user_id=self.user_id, status="pending")
        appointments = list_appointments(user_id=self.user_id, status="scheduled")

        documents = []

        # Tareas
        for t in tasks:
            doc = f"Tarea: {t['title']} - {t['description']} - Prioridad: {t['priority']} - Vence: {t['due_date']}"
            documents.append(doc)

        # Citas
        for a in appointments:
            doc = f"Cita: {a['title']} - {a['description']} - Fecha: {a['start_datetime']} - Ubicación: {a['location']}"
            documents.append(doc)

        self.embedding_store.add_documents(
            documents=documents,
            index_key=f"personal_user_{self.user_id}"
        )

    def search_relevant_items(self, query: str, limit: int = 3):
        """Búsqueda semántica de tareas y citas."""
        results = self.embedding_store.search(
            query=query,
            top_k=limit,
            index_key=f"personal_user_{self.user_id}"
        )
        return results
```

**3.3. Auto-indexación al Crear/Actualizar**

```python
# app/api/routers/user/products.py (modificar)

@router.post("/")
async def create_product(
    product: ProductCreate,
    current_user = Depends(get_current_regular_user)
):
    """Crea un producto y lo indexa automáticamente."""
    product_id = create_product_db(
        user_id=current_user['id'],
        **product.dict()
    )

    # Auto-indexar
    assistant = CommercialAssistant(user_id=current_user['id'])
    assistant.index_products()

    return {"id": product_id, "indexed": True}
```

**3.4. Endpoint de Re-indexación Manual**

```python
# app/api/routers/user/chat.py (nuevo)

@router.post("/reindex/products")
async def reindex_products(
    current_user = Depends(get_current_regular_user)
):
    """Re-indexa todos los productos del usuario."""
    assistant = CommercialAssistant(user_id=current_user['id'])
    assistant.index_products()
    return {"success": True, "message": "Productos re-indexados"}

@router.post("/reindex/personal")
async def reindex_personal(
    current_user = Depends(get_current_regular_user)
):
    """Re-indexa tareas y citas del usuario."""
    assistant = PersonalAssistant(user_id=current_user['id'])
    assistant.index_tasks_and_appointments()
    return {"success": True, "message": "Agenda re-indexada"}
```

**Estimación**:
- CommercialAssistant RAG: 150 líneas modificadas
- PersonalAssistant RAG: 100 líneas modificadas
- Auto-indexación hooks: 80 líneas
- Endpoints: 60 líneas
- **Total**: ~390 líneas
- **Tiempo**: 3-4 días

---

### Fase 2: IMPORTANTE - Mejoras de UX y Analytics (Prioridad MEDIA)

#### Sprint 5.4: Dashboard de Analytics Avanzado 📊

**Objetivos:**
1. Gráficos interactivos de uso de asistentes
2. Análisis de conversaciones (temas más consultados)
3. Métricas de productos más vendidos/consultados
4. Reportes de productividad (tareas completadas, citas cumplidas)
5. Exportación de reportes en PDF/CSV

**Componentes:**
- `templates/user/analytics.html`: Dashboard visual con Chart.js
- `app/api/routers/user/analytics.py`: Endpoints de analytics
- `app/utils/export.py`: Generación de PDF/CSV

**Endpoints:**
```python
GET /api/user/analytics/conversations
GET /api/user/analytics/products-popular
GET /api/user/analytics/productivity
GET /api/user/analytics/assistant-usage
POST /api/user/analytics/export?format=pdf|csv
```

**Estimación**: 400 líneas, 3 días

---

#### Sprint 5.5: Panel de Entrenamiento Mejorado 🎓

**Problema Actual:**
- UI básica funcional
- Falta feedback en tiempo real durante entrenamiento
- No hay visualización de métricas (loss, epochs)
- No se pueden cancelar entrenamientos en curso

**Objetivos:**
1. Progress bar en tiempo real con WebSocket
2. Gráficos de loss por epoch
3. Cancelación de entrenamientos
4. Historial de entrenamientos con métricas
5. Comparación de modelos entrenados

**Componentes:**
- WebSocket para progreso en tiempo real
- Gráficos con Chart.js
- Tabla de comparación de modelos

**Estimación**: 350 líneas, 3 días

---

#### Sprint 5.6: Exportación de Datos 📁

**Objetivos:**
1. Exportar productos a CSV
2. Exportar tareas/citas a CSV/ICS (calendario)
3. Exportar conversaciones a PDF
4. Backup completo de datos del usuario en ZIP

**Endpoints:**
```python
GET /api/user/export/products?format=csv
GET /api/user/export/tasks?format=csv
GET /api/user/export/appointments?format=ics
GET /api/user/export/conversations?format=pdf
GET /api/user/export/full-backup
```

**Estimación**: 250 líneas, 2 días

---

### Fase 3: DESEABLE - Optimización y Escalabilidad (Prioridad BAJA)

#### Sprint 5.7: Rate Limiting por Usuario 🚦

**Objetivos:**
1. Rate limiting diferenciado por usuario
2. Límites configurables según plan (free/premium)
3. Dashboard de uso de cuota
4. Alertas cuando se acerca al límite

**Implementación:**
- Middleware personalizado
- Redis para contadores (opcional)
- DB para tracking de uso

**Estimación**: 200 líneas, 2 días

---

#### Sprint 5.8: Tests de Integración Completos ✅

**Objetivos:**
1. Tests E2E de flujos completos
2. Tests de integración WhatsApp (mock)
3. Tests de RAG y embeddings
4. Coverage > 80%

**Archivos:**
```
tests/integration/
  test_whatsapp_flow.py
  test_rag_commercial.py
  test_rag_personal.py
  test_reminders_e2e.py
  test_training_flow.py
```

**Estimación**: 600 líneas, 4 días

---

#### Sprint 5.9: Documentación API (Swagger) 📚

**Objetivos:**
1. Documentación automática con FastAPI
2. Ejemplos de uso para cada endpoint
3. Autenticación en Swagger UI
4. Exportar a OpenAPI 3.0

**Implementación:**
```python
# app/main.py
app = FastAPI(
    title="SimpleIA API",
    description="API multi-tenant para asistentes IA",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Agregar ejemplos a todos los modelos Pydantic
class ProductCreate(BaseModel):
    name: str
    description: str
    price: float

    class Config:
        schema_extra = {
            "example": {
                "name": "Laptop Dell XPS",
                "description": "Laptop de alta gama",
                "price": 1500.00
            }
        }
```

**Estimación**: 150 líneas, 1 día

---

#### Sprint 5.10: Multi-idioma (i18n) 🌍

**Objetivos:**
1. Soporte para inglés y español
2. Detección automática de idioma del usuario
3. Templates con traducciones
4. Mensajes de asistentes en idioma del usuario

**Implementación:**
- Flask-Babel o similar
- Archivos de traducción `.po`
- Detector de idioma en mensajes

**Estimación**: 400 líneas, 3 días

---

## 📊 Resumen de Estimaciones

### Fase 1: CRÍTICA (Prioridad ALTA)
| Sprint | Descripción | Líneas | Días | Prioridad |
|--------|------------|--------|------|-----------|
| 5.1 | Integración WhatsApp Real | 500 | 3-4 | ⚠️ CRÍTICO |
| 5.2 | Sistema de Recordatorios Completo | 390 | 2-3 | ⚠️ CRÍTICO |
| 5.3 | RAG con Embeddings | 390 | 3-4 | 🔥 ALTA |
| **TOTAL FASE 1** | | **1,280** | **8-11** | |

### Fase 2: IMPORTANTE (Prioridad MEDIA)
| Sprint | Descripción | Líneas | Días | Prioridad |
|--------|------------|--------|------|-----------|
| 5.4 | Dashboard Analytics Avanzado | 400 | 3 | 📊 MEDIA |
| 5.5 | Panel Entrenamiento Mejorado | 350 | 3 | 🎓 MEDIA |
| 5.6 | Exportación de Datos | 250 | 2 | 📁 MEDIA |
| **TOTAL FASE 2** | | **1,000** | **8** | |

### Fase 3: DESEABLE (Prioridad BAJA)
| Sprint | Descripción | Líneas | Días | Prioridad |
|--------|------------|--------|------|-----------|
| 5.7 | Rate Limiting por Usuario | 200 | 2 | 🚦 BAJA |
| 5.8 | Tests de Integración | 600 | 4 | ✅ BAJA |
| 5.9 | Documentación API (Swagger) | 150 | 1 | 📚 BAJA |
| 5.10 | Multi-idioma (i18n) | 400 | 3 | 🌍 BAJA |
| **TOTAL FASE 3** | | **1,350** | **10** | |

**TOTAL GENERAL M5**: ~3,630 líneas, 26-29 días de desarrollo

---

## 🎯 Plan de Implementación Recomendado

### Opción A: Full M5 (26-29 días)
Implementar las 3 fases completas en orden de prioridad.

### Opción B: M5 Core (8-11 días) ⭐ RECOMENDADO
Implementar solo Fase 1 (Crítica) para tener un producto funcional completo:
1. WhatsApp funcionando
2. Recordatorios por WhatsApp/Email
3. RAG con embeddings para asistentes inteligentes

### Opción C: M5 Extendido (16-19 días)
Fase 1 + Fase 2 (sin Fase 3):
- Core funcional + Analytics + UX mejorada
- Dejar tests y optimización para iteraciones futuras

---

## 🔧 Configuración Requerida para M5

### Variables de Entorno Nuevas

```bash
# .env

# WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_VERIFY_TOKEN=

# Email SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=

# Embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_INDEX_PATH=./data/embeddings

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_FREE_TIER=100
RATE_LIMIT_PREMIUM_TIER=1000

# Analytics
ANALYTICS_ENABLED=true
ANALYTICS_RETENTION_DAYS=90
```

### Dependencias Nuevas

```txt
# requirements.txt (agregar)

# Email
aiosmtplib==2.0.2

# Exportación
reportlab==4.0.7  # PDF
python-icalendar==5.0.11  # ICS calendar

# WebSockets (para training progress)
websockets==12.0

# i18n (opcional)
flask-babel==4.0.0
```

---

## 📝 Notas de Implementación

### Consideraciones de Seguridad

1. **Tokens WhatsApp**: Almacenar en variables de entorno, nunca en código
2. **Email SMTP**: Usar OAuth2 en lugar de contraseñas cuando sea posible
3. **Rate Limiting**: Evitar DDoS y abuso de API
4. **Validación de Webhooks**: Verificar firma de WhatsApp
5. **Sanitización**: Validar todos los inputs de usuarios

### Consideraciones de Performance

1. **Embeddings**: Cachear embeddings de productos (no re-generar en cada búsqueda)
2. **WhatsApp**: Usar queue para mensajes (evitar timeouts)
3. **Indexación**: Hacer re-indexación en background task
4. **Analytics**: Pre-calcular métricas cada hora (no en tiempo real)

### Consideraciones de Escalabilidad

1. **Redis**: Considerar Redis para cache distribuido (en lugar de LRU in-memory)
2. **Queue**: Implementar Celery o RQ para tareas asíncronas (reminders, indexación)
3. **DB**: Considerar PostgreSQL para producción (mejor que SQLite)
4. **Storage**: S3 para archivos de entrenamiento y exportaciones

---

## 🚀 Quick Start M5 (Fase 1 - Core)

### Semana 1: WhatsApp
- Día 1-2: Setup WhatsApp Business API, DB, cliente
- Día 3-4: Webhook real, envío de mensajes, tests

### Semana 2: Recordatorios + RAG
- Día 1-2: Email client, preferencias, historial
- Día 3-4: RAG en CommercialAssistant, auto-indexación

### Semana 3: Integración y Tests
- Día 1: RAG en PersonalAssistant
- Día 2-3: Tests de integración completos
- Día 4: Documentación y deploy

**Resultado**: Sistema completamente funcional con las 3 características críticas implementadas.

---

## ✅ Criterios de Aceptación M5

### Fase 1 (CRÍTICA):
- ✅ Usuario puede vincular WhatsApp y recibir mensajes del asistente
- ✅ Recordatorios se envían por WhatsApp/Email según preferencias
- ✅ Asistente comercial usa RAG para búsqueda semántica de productos
- ✅ Búsqueda de productos muestra resultados relevantes (no solo keywords)

### Fase 2 (IMPORTANTE):
- ✅ Dashboard de analytics muestra gráficos de uso
- ✅ Panel de entrenamiento muestra progreso en tiempo real
- ✅ Usuario puede exportar sus datos en CSV/PDF

### Fase 3 (DESEABLE):
- ✅ Rate limiting por usuario funciona correctamente
- ✅ Coverage de tests > 80%
- ✅ Documentación Swagger accesible en /docs
- ✅ Soporte para inglés y español

---

## 🎉 Conclusión

**M5 convierte el proyecto de un prototipo funcional a un producto listo para producción**, completando las funcionalidades core que quedaron parcialmente implementadas y agregando características avanzadas de analytics y UX.

**Recomendación**: Implementar **Fase 1 (Core)** primero para validar con usuarios reales, luego iterar con Fases 2 y 3 según feedback.
