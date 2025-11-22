# Módulo 4 (M4): Asistentes Contextuales Multi-Tenant

## Visión General

El Módulo 4 implementa un sistema de asistentes inteligentes con aislamiento multi-tenant, permitiendo a cada usuario tener:

- **Asistente Comercial**: Gestión de catálogo de productos y consultas comerciales
- **Asistente Personal**: Agenda, tareas y productividad personal
- **Integración WhatsApp**: Comunicación bidireccional automática
- **Sistema de Recordatorios**: Notificaciones proactivas
- **Analytics**: Seguimiento de uso y conversaciones

## Arquitectura Multi-Tenant

### Principios de Aislamiento

- **Por Usuario**: Todos los datos están segregados por `user_id`
- **Roles**: `superadmin` (gestión del sistema) vs `user` (datos personales)
- **Paneles Separados**: `/admin/*` y `/user/*`
- **Seguridad**: Validación en cada query con `user_id`

## Sprints Implementados

### ✅ Sprint M4.1: Base Multi-Tenant

**Objetivo**: Establecer la infraestructura de aislamiento de usuarios

**Componentes**:

- `app/db/sqlite.py`: Actualizado con columnas `role` y `created_at`
- `app/security/auth.py`: Funciones de autenticación por rol
  - `get_current_superadmin()`: Solo superadmins
  - `get_current_regular_user()`: Solo usuarios regulares
- `app/api/routers/auth.py`: Login/registro con roles
- `app/migrations/migrate_m4_1.py`: Migración de esquema

**Bases de Datos**:

```sql
-- Tabla users actualizada
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    hashed_password TEXT,
    is_admin INTEGER DEFAULT 0,
    role TEXT DEFAULT 'user',  -- 'user' | 'superadmin'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Flujo de Autenticación**:

1. Login → JWT con `{sub, is_admin, role, user_id}`
2. Redirección según rol:
   - `superadmin` → `/admin/dashboard`
   - `user` → `/user/dashboard`

---

### ✅ Sprint M4.2: Base de Datos Productos Comercial

**Objetivo**: CRUD de productos con aislamiento por usuario

**Componentes**:

- `app/db/products.py`: Funciones de base de datos
- `app/api/routers/user/products.py`: API REST completa
- `templates/user/commercial/products.html`: Interfaz de gestión

**Base de Datos**:

```sql
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,  -- Aislamiento
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    sku TEXT,
    category TEXT,
    stock INTEGER DEFAULT 0,
    active INTEGER DEFAULT 1,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Endpoints**:

- `POST /api/user/products/` - Crear producto
- `GET /api/user/products/` - Listar productos (con filtros)
- `GET /api/user/products/{id}` - Obtener producto
- `PUT /api/user/products/{id}` - Actualizar producto
- `DELETE /api/user/products/{id}` - Eliminar producto (soft delete)
- `GET /api/user/products/categories` - Listar categorías
- `GET /api/user/products/count` - Contar productos

**Características**:

- Búsqueda por nombre, SKU, categoría
- Filtrado por estado (activo/inactivo)
- Gestión de stock
- Soft delete (campo `active`)

---

### ✅ Sprint M4.3: Asistente Comercial LLM

**Objetivo**: Asistente inteligente para consultas de productos

**Componentes**:

- `app/assistants/base.py`: Clase base abstracta
- `app/assistants/commercial.py`: Asistente comercial

**Funcionalidades**:

```python
class CommercialAssistant(BaseAssistant):
    def get_context(self) -> Dict:
        # Obtiene productos del usuario

    def build_system_prompt(self) -> str:
        # Construye prompt con catálogo

    def search_relevant_products(self, query: str) -> List:
        # Búsqueda semántica de productos

    async def process_message(self, message: str) -> str:
        # Genera respuesta contextual
```

**Capacidades**:

- Consultar precios y disponibilidad
- Recomendar productos similares
- Informar sobre stock
- Búsqueda por nombre, categoría, SKU
- Respuestas contextualizadas al catálogo del usuario

**System Prompt**:

- Incluye resumen del catálogo (hasta 50 productos)
- Lista de categorías disponibles
- Información de stock
- Instrucciones de comportamiento

---

### ✅ Sprint M4.4: Base de Datos Agenda Personal

**Objetivo**: Gestión de citas y tareas

**Componentes**:

- `app/db/personal.py`: Funciones para appointments y tasks
- `app/api/routers/user/personal.py`: API REST

**Bases de Datos**:

```sql
-- Citas
CREATE TABLE appointments (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    start_datetime TIMESTAMP NOT NULL,
    end_datetime TIMESTAMP,
    location TEXT,
    attendees TEXT,
    reminder_minutes INTEGER DEFAULT 15,
    status TEXT DEFAULT 'scheduled',
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Tareas
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    due_date DATE,
    priority TEXT DEFAULT 'medium',  -- low|medium|high
    status TEXT DEFAULT 'pending',    -- pending|in_progress|completed
    category TEXT,
    reminder_minutes INTEGER DEFAULT 60,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    completed_at TIMESTAMP
);
```

**Endpoints Appointments**:

- `POST /api/user/personal/appointments` - Crear cita
- `GET /api/user/personal/appointments` - Listar citas
- `PUT /api/user/personal/appointments/{id}` - Actualizar
- `DELETE /api/user/personal/appointments/{id}` - Eliminar

**Endpoints Tasks**:

- `POST /api/user/personal/tasks` - Crear tarea
- `GET /api/user/personal/tasks` - Listar tareas
- `PUT /api/user/personal/tasks/{id}` - Actualizar
- `DELETE /api/user/personal/tasks/{id}` - Eliminar
- `GET /api/user/personal/tasks/categories` - Categorías

---

### ✅ Sprint M4.5: Asistente Personal LLM

**Objetivo**: Asistente para productividad y organización

**Componentes**:

- `app/assistants/personal.py`: Asistente personal

**Funcionalidades**:

```python
class PersonalAssistant(BaseAssistant):
    def get_context(self) -> Dict:
        # Citas próximas + tareas pendientes

    def get_upcoming_appointments(self, days=7) -> List:
        # Citas de próximos N días

    def get_pending_tasks_by_priority() -> Dict:
        # Tareas agrupadas por prioridad

    def get_overdue_tasks() -> List:
        # Tareas vencidas

    async def process_message(self, message: str) -> str:
        # Respuesta contextual con agenda
```

**Capacidades**:

- Consultar agenda y próximas citas
- Gestionar tareas (crear, actualizar, priorizar)
- Recordar compromisos y fechas límite
- Detectar conflictos de horarios
- Sugerir organización de tiempo
- Lenguaje proactivo y motivador

**System Prompt**:

- Estado de agenda (citas programadas)
- Tareas pendientes con prioridades
- Tareas vencidas (alertas)
- Instrucciones de comportamiento

---

### ✅ Sprint M4.6: Integración WhatsApp

**Objetivo**: Webhook para WhatsApp Business API

**Componentes**:

- `app/api/routers/whatsapp.py`: Endpoints de WhatsApp

**Endpoints**:

```python
POST /api/whatsapp/webhook
    # Procesa mensajes entrantes
    # Detecta intención (comercial/personal)
    # Enruta al asistente apropiado

GET /api/whatsapp/verify
    # Verificación de webhook (requerido por WhatsApp)

POST /api/whatsapp/link-phone
    # Vincula número de teléfono con user_id

POST /api/whatsapp/send
    # Envía mensaje outbound (placeholder)
```

**Detección de Intención**:

```python
def detect_intent(message: str) -> str:
    # Palabras clave comerciales:
    # producto, precio, comprar, stock, catálogo

    # Palabras clave personales:
    # cita, reunión, agenda, tarea, recordar

    # Retorna 'commercial' o 'personal'
```

**Flujo de Procesamiento**:

1. Mensaje entrante → `/whatsapp/webhook`
2. Identificar usuario por teléfono
3. Detectar intención (o usar contexto)
4. Enrutar a `CommercialAssistant` o `PersonalAssistant`
5. Generar respuesta
6. Retornar para envío por WhatsApp

**TODO en Producción**:

- Integrar con WhatsApp Business API real
- Configurar tokens de verificación
- Implementar envío de mensajes outbound
- Almacenar mapeo phone → user_id en DB

---

### ✅ Sprint M4.7: Sistema de Recordatorios

**Objetivo**: Scheduler para notificaciones automáticas

**Componentes**:

- `app/core/reminders.py`: Scheduler de recordatorios

**Funcionalidades**:

```python
class ReminderScheduler:
    async def check_appointment_reminders():
        # Verifica citas próximas
        # Envía recordatorios según reminder_minutes

    async def check_task_reminders():
        # Verifica tareas próximas a vencer
        # Envía alertas de fechas límite

    async def send_reminder(user_id, type, title, details):
        # Envía notificación (WhatsApp/email)

    async def run():
        # Loop continuo con intervalo configurable
```

**Configuración**:

- Intervalo de verificación: 5 minutos (configurable)
- Cache de recordatorios enviados (evita duplicados)
- Limpieza automática de cache

**Tipos de Recordatorios**:

1. **Citas**: `reminder_minutes` antes del `start_datetime`
2. **Tareas**: `reminder_minutes` antes del `due_date`

**Ejecución**:

```bash
# Como servicio independiente
python app/core/reminders.py

# O integrado en main.py con background task
```

**TODO**:

- Conectar con router de WhatsApp para envío real
- Configurar preferencias de usuario (horarios, canales)
- Dashboard admin para monitoreo de scheduler

---

### ✅ Sprint M4.8: Contexto y Analytics

**Objetivo**: Historial de conversaciones y métricas de uso

**Componentes**:

- `app/db/conversations.py`: Gestión de conversaciones
- `app/api/routers/user/chat.py`: API de chat

**Bases de Datos**:

```sql
-- Conversaciones
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    assistant_type TEXT NOT NULL,  -- commercial|personal
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Mensajes
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    conversation_id INTEGER NOT NULL,
    role TEXT NOT NULL,  -- user|assistant
    content TEXT NOT NULL,
    created_at TIMESTAMP
);

-- Analytics
CREATE TABLE user_analytics (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    event_data TEXT,
    created_at TIMESTAMP
);
```

**Endpoints Chat**:

```python
POST /api/user/chat/message
    # Envía mensaje y obtiene respuesta
    # Mantiene historial de conversación

GET /api/user/chat/conversations
    # Lista conversaciones del usuario

GET /api/user/chat/conversations/{id}
    # Obtiene conversación con mensajes

DELETE /api/user/chat/conversations/{id}
    # Elimina conversación

GET /api/user/chat/stats
    # Estadísticas de uso del usuario

GET /api/user/chat/activity
    # Actividad reciente (últimos N días)
```

**Funcionalidades Analytics**:

```python
def get_user_stats(user_id) -> Dict:
    # Total de conversaciones
    # Total de mensajes
    # Conversaciones por tipo (commercial/personal)
    # Eventos más frecuentes

def get_recent_activity(user_id, days=7) -> List:
    # Actividad reciente
    # Eventos ordenados por fecha
```

**Tracking de Eventos**:

- `message_sent` - Mensaje enviado
- `product_query` - Consulta de producto
- `task_created` - Tarea creada
- `appointment_created` - Cita creada
- etc.

---

## Estructura de Archivos

```
app/
├── assistants/
│   ├── __init__.py
│   ├── base.py              # Clase base abstracta
│   ├── commercial.py        # Asistente comercial
│   └── personal.py          # Asistente personal
│
├── db/
│   ├── sqlite.py            # Users con roles
│   ├── products.py          # Productos comerciales
│   ├── personal.py          # Appointments y tasks
│   └── conversations.py     # Chat y analytics
│
├── api/routers/
│   ├── auth.py              # Login/registro con roles
│   ├── whatsapp.py          # Webhook WhatsApp
│   └── user/
│       ├── dashboard.py     # Dashboard usuario
│       ├── products.py      # API productos
│       ├── personal.py      # API agenda/tareas
│       └── chat.py          # API conversaciones
│
├── core/
│   └── reminders.py         # Scheduler de recordatorios
│
├── migrations/
│   └── migrate_m4_1.py      # Migración roles
│
└── main.py                  # FastAPI app con routers

templates/
├── user/
│   ├── user_layout.html     # Layout panel usuario
│   ├── dashboard.html       # Dashboard principal
│   └── commercial/
│       └── products.html    # Gestión productos
│
└── admin/                   # Panel superadmin (existente)

feedback/                    # Directorio de bases de datos
├── users.sqlite             # Usuarios y auth
├── products.sqlite          # Productos por usuario
├── personal.sqlite          # Agenda y tareas
├── conversations.sqlite     # Chat y analytics
└── feedback.sqlite          # Feedback (existente)
```

---

## Flujos de Uso

### 1. Usuario Normal - Gestión de Productos

```
1. Login → Redirección a /user/dashboard
2. Clic en "Productos" → /user/commercial/products
3. "Agregar Producto" → Modal con formulario
4. Guardar → POST /api/user/products/
5. Lista actualizada (solo productos del usuario)
```

### 2. Usuario Normal - Asistente Comercial

```
1. Desde /user/dashboard → "Chat Comercial"
2. Mensaje: "¿Cuánto cuesta el producto X?"
3. POST /api/user/chat/message {
     content: "...",
     assistant_type: "commercial"
   }
4. CommercialAssistant busca productos relevantes
5. Genera respuesta contextual con precios/stock
6. Respuesta guardada en historial
```

### 3. Usuario Normal - Recordatorio de Cita

```
1. Crear cita → POST /api/user/personal/appointments {
     title: "Reunión cliente",
     start_datetime: "2025-11-22 10:00",
     reminder_minutes: 30
   }
2. Scheduler verifica cada 5 minutos
3. A las 09:30 → send_reminder()
4. Notificación por WhatsApp (si configurado)
```

### 4. Cliente Externo - WhatsApp

```
1. Cliente envía WhatsApp: "¿Tienen laptops?"
2. WhatsApp → POST /api/whatsapp/webhook {
     phone_number: "+123456789",
     message: "¿Tienen laptops?"
   }
3. Sistema identifica user_id por teléfono
4. detect_intent() → "commercial"
5. CommercialAssistant procesa mensaje
6. Respuesta: "Sí, tenemos 3 modelos: ..."
7. Sistema envía respuesta por WhatsApp
```

---

## Seguridad Multi-Tenant

### Validación en Cada Endpoint

```python
# ✅ CORRECTO
@router.get("/products")
async def list_products(current_user = Depends(get_current_regular_user)):
    products = products_db.list_products(
        user_id=current_user["id"]  # Filtrado por user_id
    )
    return products

# ❌ INCORRECTO (sin filtrado)
@router.get("/products")
async def list_products():
    products = products_db.list_products()  # Retorna TODOS los productos
    return products
```

### Queries con Aislamiento

```python
# Siempre incluir user_id en WHERE
cursor.execute("""
    SELECT * FROM products
    WHERE user_id = ? AND id = ?
""", (user_id, product_id))

# Nunca permitir acceso sin verificar user_id
cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))  # ❌
```

### Roles y Permisos

```python
# Superadmin - Solo gestión del sistema
@router.get("/admin/users", dependencies=[Depends(get_current_superadmin)])

# User - Solo sus propios datos
@router.get("/user/products", dependencies=[Depends(get_current_regular_user)])

# Bloqueo cruzado
if user.get("role") == "superadmin":
    return RedirectResponse("/admin/dashboard")  # No accede a /user/*
```

---

## TODOs para Producción

### Prioridad Alta

1. **LLM Provider**: Conectar asistentes con OpenAI/Claude/otro
2. **WhatsApp Real**: Implementar integración con Business API
3. **Embeddings**: Búsqueda semántica real de productos
4. **Tests**: Cobertura de endpoints y asistentes

### Prioridad Media

5. **Templates Completos**: Interfaces para tasks, appointments
6. **Exportación**: CSV/PDF de productos, tareas, citas
7. **Configuración Usuario**: Preferencias de recordatorios
8. **Dashboard Analytics**: Gráficos de uso

### Prioridad Baja

9. **Notificaciones Email**: Alternativa a WhatsApp
10. **API Rate Limiting**: Por usuario
11. **Webhooks Personalizados**: Para integraciones externas
12. **Modo Multi-Idioma**: i18n

---

## Comandos de Ejecución

```bash
# Migración de base de datos
python3 app/migrations/migrate_m4_1.py

# Servidor API
./run_llm.sh api
# o
uvicorn app.main:app --reload --port 8000

# Servidor cliente web
./run_llm.sh client
# o
python app/llm_client.py

# Scheduler de recordatorios (independiente)
python app/core/reminders.py

# Tests (cuando estén implementados)
pytest tests/
```

---

## Integración con LLM Compartido

### Arquitectura de Compartición

**Principio**: Un solo modelo LLM para toda la aplicación, datos aislados por usuario.

**Componentes**:

1. **`model_manager.py`** (Global)

   - Mantiene `_provider_instance` (única instancia del LLM)
   - Configurado desde `config/config.json`
   - Cargado al iniciar en `main.py` con `load_model()`

2. **`CommercialAssistant` / `PersonalAssistant`** (Por Usuario)

   - Reciben `user_id` en constructor
   - Filtran datos solo de ese usuario
   - Usan `llm_provider` compartido para generar respuestas

3. **Aislamiento de Datos**
   - `products` filtrados por `user_id`
   - `tasks/appointments` filtrados por `user_id`
   - `conversations` filtradas por `user_id`

### Flujo de Procesamiento

```
Usuario hace pregunta en chat
    ↓
JWT extrae user_id del token
    ↓
Assistant(user_id) carga solo SUS datos desde DB
    ↓
build_system_prompt() con contexto del usuario
    ↓
llm_provider.generate() ← MODELO COMPARTIDO
    ↓
Respuesta guardada en conversation del usuario
```

### Ventajas de Este Diseño

✅ **Eficiencia**: Un solo modelo en memoria (ahorro de RAM)  
✅ **Consistencia**: Todos los usuarios tienen misma calidad de respuestas  
✅ **Entrenamiento Centralizado**: Fine-tuning afecta a todos los usuarios  
✅ **Configuración Simple**: Admin cambia modelo → todos lo usan inmediatamente  
✅ **Seguridad**: Datos nunca se filtran entre usuarios (filtrado por user_id)

### Configuración en Producción

```json
// config/config.json
{
  "provider": "claude",
  "selected_model": "claude-3-5-sonnet-20241022",
  "anthropic_api_key": "sk-ant-..."
}
```

Cuando admin cambia el modelo:

1. `model_manager.load_model(force=True)` recarga el provider
2. Nueva instancia global reemplaza la anterior
3. **Todos** los usuarios usan nuevo modelo inmediatamente
4. Datos históricos y conversaciones permanecen intactos

### Ejemplo de Uso Simultáneo

```python
# USUARIO 1 pregunta en chat comercial
"¿Cuánto cuestan las laptops?"
→ CommercialAssistant(user_id=1)
→ SELECT * FROM products WHERE user_id=1
→ llm_provider.generate(prompt + productos_user1)
→ Respuesta guardada en conversations (user_id=1)

# USUARIO 2 pregunta en chat personal (al mismo tiempo)
"¿Qué tengo pendiente mañana?"
→ PersonalAssistant(user_id=2)
→ SELECT * FROM tasks WHERE user_id=2
→ llm_provider.generate(prompt + tareas_user2)  # MISMO LLM
→ Respuesta guardada en conversations (user_id=2)
```

**Resultado**: Ambos usan el mismo Claude/GPT, pero cada uno ve solo sus propios datos.

---

## Conclusión

El Módulo 4 proporciona una plataforma completa de asistentes contextuales con:

✅ **Aislamiento multi-tenant** robusto  
✅ **Dos asistentes especializados** (comercial + personal)  
✅ **LLM compartido** conectado (model_manager)  
✅ **Integración WhatsApp** preparada  
✅ **Sistema de recordatorios** automático  
✅ **Analytics y seguimiento** de uso

**Estado**: Todos los sprints completados. LLM integrado. Listo para producción.
