# M3 - Diseño: Panel de Administración Web y Mejoras UI

**Fecha**: 20 de noviembre de 2025  
**Milestone**: M3 - Admin Panel Web, Gestión Usuarios, UI/UX Mejorada  
**Estado**: 📋 EN DISEÑO

---

## Objetivos Principales M3

1. **Panel de Administración Web Completo**

   - Gestión de usuarios con roles (admin/user)
   - Gestión de feedback
   - Configuración de providers y reload
   - Visualización de métricas y estadísticas
   - Gestión de entrenamientos

2. **Sistema de Roles y Permisos**

   - Primer usuario registrado = admin automático
   - CLI para asignar/revocar permisos admin
   - Protección de rutas admin

3. **Mejoras Estéticas Cliente Web**

   - CSS modular separado
   - Diseño responsive (mobile-first)
   - Personalización de marca (nombre app, nombre LLM)
   - Tema moderno y accesible

4. **Configuración Personalizable**
   - Nombre de la aplicación/cliente web
   - Nombre del LLM (personalidad)
   - Logo y colores de marca

---

## Sprint M3.1: Sistema de Roles y Permisos

### Objetivo

Implementar sistema de roles (admin/user) con primer usuario como admin automático.

### Tareas

#### 1.1. Modificar Base de Datos Usuarios

**Archivo**: `app/db/sqlite.py`

**Cambios**:

```sql
-- Agregar columna is_admin a tabla users
ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP;
```

**Nuevas funciones**:

- `is_first_user() -> bool`: Verificar si es el primer usuario
- `set_admin(username: str, is_admin: bool)`: Asignar/revocar admin
- `get_user_with_role(username: str) -> dict`: Obtener usuario con rol
- `list_users_with_roles() -> list[dict]`: Listar todos los usuarios

**Líneas estimadas**: +60

#### 1.2. Middleware Autenticación con Roles

**Archivo**: `app/security/auth.py`

**Cambios**:

- Modificar `get_current_user()` para incluir `is_admin` en payload JWT
- Crear `get_current_admin_user()`: Dependency para rutas admin
- Agregar `is_admin: bool` en token data

**Nuevas funciones**:

```python
def get_current_admin_user(current_user: User = Depends(get_current_user)):
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
```

**Líneas estimadas**: +30

#### 1.3. Lógica Primer Usuario Admin

**Archivo**: `app/api/routers/auth.py`

**Cambios**:

```python
@router.post("/register")
async def register(user: UserCreate):
    # Verificar si es primer usuario
    is_first = is_first_user()

    # Crear usuario
    create_user(user.username, hashed_password)

    # Si es primero, hacerlo admin
    if is_first:
        set_admin(user.username, True)
        return {"message": "First user registered as admin", "is_admin": True}

    return {"message": "User registered", "is_admin": False}
```

**Líneas estimadas**: +15

#### 1.4. CLI Admin - Gestión Roles

**Archivo**: `app/admin_cli.py`

**Nuevos comandos**:

- `users list`: Listar usuarios con roles
- `users grant-admin <username>`: Otorgar permisos admin
- `users revoke-admin <username>`: Revocar permisos admin
- `users info <username>`: Ver detalles de usuario

**Ejemplo uso**:

```bash
./run_llm.sh admin users list
./run_llm.sh admin users grant-admin juan
./run_llm.sh admin users revoke-admin pedro
```

**Líneas estimadas**: +80

---

## Sprint M3.2: Panel Admin Web - Gestión Usuarios

### Objetivo

Crear interfaz web para administrar usuarios.

### Tareas

#### 2.1. Backend API Gestión Usuarios

**Archivo**: `app/api/routers/admin.py`

**Nuevos endpoints**:

```python
# Listar usuarios (con paginación)
GET /admin/users?page=1&limit=20
Response: {
  "users": [
    {"id": 1, "username": "admin", "is_admin": true, "created_at": "2025-11-20"},
    ...
  ],
  "total": 50,
  "page": 1,
  "pages": 3
}

# Modificar rol de usuario
POST /admin/users/{user_id}/role
Body: {"is_admin": true}
Response: {"message": "Role updated"}

# Eliminar usuario
DELETE /admin/users/{user_id}
Response: {"message": "User deleted"}

# Resetear contraseña (generar temporal)
POST /admin/users/{user_id}/reset-password
Response: {"temp_password": "random123"}
```

**Líneas estimadas**: +120

#### 2.2. Frontend Panel Usuarios

**Archivo**: `templates/admin_users.html`

**Componentes**:

- Tabla usuarios con columnas: ID, Username, Role, Created At, Actions
- Botones: Grant Admin, Revoke Admin, Delete, Reset Password
- Paginación
- Búsqueda por username
- Filtro por rol (All/Admin/User)

**Tecnologías**:

- HTML5 + CSS3 (responsive)
- JavaScript vanilla (fetch API)
- Confirmaciones antes de delete

**Líneas estimadas**: +250

---

## Sprint M3.3: Panel Admin Web - Gestión Feedback

### Objetivo

Interfaz web para visualizar, filtrar y gestionar feedback.

### Tareas

#### 3.1. Backend API Gestión Feedback

**Archivo**: `app/api/routers/admin.py`

**Nuevos endpoints**:

```python
# Listar feedback (con filtros y paginación)
GET /admin/feedback?page=1&limit=20&search=query&date_from=2025-11-01
Response: {
  "feedback": [
    {"id": 1, "text": "...", "timestamp": "2025-11-20 10:30", "used_training": false},
    ...
  ],
  "total": 200,
  "page": 1
}

# Marcar feedback como usado en entrenamiento
POST /admin/feedback/{id}/mark-used
Response: {"message": "Marked as used"}

# Eliminar feedback
DELETE /admin/feedback/{id}
Response: {"message": "Feedback deleted"}

# Exportar feedback (CSV/JSON)
GET /admin/feedback/export?format=csv
Response: file download
```

**Modificar tabla feedback**:

```sql
ALTER TABLE feedback ADD COLUMN used_training BOOLEAN DEFAULT FALSE;
```

**Líneas estimadas**: +100

#### 3.2. Frontend Panel Feedback

**Archivo**: `templates/admin_feedback.html`

**Componentes**:

- Tabla feedback: ID, Text (preview), Timestamp, Used, Actions
- Búsqueda full-text
- Filtro por fecha
- Filtro por usado/no usado
- Botón exportar
- Botón marcar como usado
- Botón delete múltiple (checkboxes)

**Líneas estimadas**: +280

---

## Sprint M3.4: Panel Admin Web - Gestión Providers

### Objetivo

Configurar y cambiar providers desde web.

### Tareas

#### 4.1. Backend API Gestión Providers

**Archivo**: `app/api/routers/admin.py`

**Nuevos endpoints**:

```python
# Listar providers disponibles
GET /admin/providers
Response: {
  "current": "hf",
  "providers": [
    {
      "id": "hf",
      "name": "HuggingFace Local",
      "status": "active",
      "models": ["gpt2", "gpt2-medium", ...],
      "requires_api_key": false
    },
    {
      "id": "claude",
      "name": "Anthropic Claude",
      "status": "configured" | "missing_key",
      "models": ["claude-3-sonnet", "claude-3-opus"],
      "requires_api_key": true,
      "api_key_set": true
    },
    ...
  ]
}

# Cambiar provider y modelo
POST /admin/providers/switch
Body: {
  "provider": "claude",
  "model": "claude-3-sonnet-20240229"
}
Response: {"message": "Provider switched, reloading...", "success": true}

# Configurar API key
POST /admin/providers/{provider_id}/api-key
Body: {"api_key": "sk-..."}
Response: {"message": "API key configured"}

# Reload modelo actual
POST /admin/providers/reload
Response: {"message": "Model reloaded"}
```

**Líneas estimadas**: +140

#### 4.2. Frontend Panel Providers

**Archivo**: `templates/admin_providers.html`

**Componentes**:

- Cards de providers con estado (active/configured/missing_key)
- Dropdown para seleccionar modelo
- Input para API key (tipo password)
- Botón "Switch & Reload"
- Indicador de provider actual
- Botón "Reload Current Model"
- Logs de último switch

**Líneas estimadas**: +220

---

## Sprint M3.5: Panel Admin Web - Métricas y Estadísticas

### Objetivo

Dashboard con métricas del sistema.

### Tareas

#### 5.1. Backend API Métricas

**Archivo**: `app/api/routers/admin.py`

**Nuevos endpoints**:

```python
# Estadísticas generales
GET /admin/stats
Response: {
  "users": {"total": 50, "admins": 2},
  "feedback": {"total": 1500, "used": 300, "unused": 1200},
  "predictions": {"total": 5000, "today": 120},
  "cache": {"size": 150, "hits": 3000, "misses": 500, "hit_rate": 0.857},
  "database": {
    "users_db_size": "2.5 MB",
    "feedback_db_size": "15.3 MB",
    "training_db_size": "8.7 MB"
  },
  "embeddings": {
    "total_documents": 1000,
    "index_size": "4.2 MB"
  },
  "training": {
    "total_runs": 5,
    "last_run": "2025-11-19 14:30",
    "status": "completed"
  }
}

# Uso por fecha (últimos 30 días)
GET /admin/usage?days=30
Response: {
  "usage": [
    {"date": "2025-11-20", "predictions": 120, "users_active": 15},
    ...
  ]
}

# Top endpoints
GET /admin/top-endpoints
Response: [
  {"endpoint": "/predict", "count": 5000, "avg_latency": 450},
  ...
]
```

**Líneas estimadas**: +180

#### 5.2. Frontend Dashboard Métricas

**Archivo**: `templates/admin_stats.html`

**Componentes**:

- Cards con stats principales (usuarios, feedback, predicciones)
- Gráficos Chart.js:
  - Uso diario (line chart)
  - Distribución endpoints (pie chart)
  - Cache hit rate (gauge)
  - Tamaño bases de datos (bar chart)
- Tabla top endpoints
- Indicadores de salud del sistema

**Líneas estimadas**: +300

---

## Sprint M3.6: Panel Admin Web - Gestión Entrenamientos

### Objetivo

Subir archivos y ejecutar entrenamientos desde web.

### Tareas

#### 6.1. Backend API Entrenamientos

**Archivo**: `app/api/routers/admin.py`

**Nuevos endpoints**:

```python
# Subir archivo de entrenamiento
POST /admin/training/upload
Content-Type: multipart/form-data
Body: file (txt/json/csv)
Response: {
  "file_id": "abc123",
  "filename": "dialogues.txt",
  "size": "2.5 MB",
  "lines": 1500
}

# Iniciar entrenamiento
POST /admin/training/start
Body: {
  "file_id": "abc123",
  "model_name": "gpt2",
  "epochs": 3,
  "batch_size": 8,
  "learning_rate": 2e-5
}
Response: {
  "run_id": 1,
  "status": "started",
  "message": "Training started in background"
}

# Estado entrenamiento
GET /admin/training/runs/{run_id}
Response: {
  "id": 1,
  "status": "running" | "completed" | "failed",
  "progress": 0.65,
  "current_epoch": 2,
  "total_epochs": 3,
  "loss": 2.345,
  "started_at": "2025-11-20 10:00",
  "estimated_completion": "2025-11-20 12:30"
}

# Cancelar entrenamiento
POST /admin/training/runs/{run_id}/cancel
Response: {"message": "Training cancelled"}

# Listar archivos subidos
GET /admin/training/files
Response: [
  {"id": "abc123", "filename": "dialogues.txt", "uploaded_at": "..."},
  ...
]
```

**Líneas estimadas**: +200

#### 6.2. Frontend Panel Entrenamientos

**Archivo**: `templates/admin_training.html`

**Componentes**:

- Upload zone (drag & drop)
- Lista archivos subidos
- Formulario configuración entrenamiento:
  - Modelo base (select)
  - Epochs (number)
  - Batch size (number)
  - Learning rate (number)
- Botón "Start Training"
- Tabla runs con:
  - ID, Status, Progress bar, Epoch, Loss, Actions
- Botón cancelar training activo
- Logs en tiempo real (WebSocket o polling)

**Líneas estimadas**: +350

---

## Sprint M3.7: Mejoras UI/UX Cliente Web

### Objetivo

Rediseñar interfaz cliente web con CSS modular y responsive.

### Tareas

#### 7.1. CSS Modular y Responsive

**Archivo**: `static/style.css` (NUEVO)

**Estructura CSS**:

```css
/* Variables CSS (tema) */
:root {
  --primary-color: #4a90e2;
  --secondary-color: #f39c12;
  --success-color: #27ae60;
  --danger-color: #e74c3c;
  --text-color: #333;
  --bg-color: #f8f9fa;
  --border-color: #dee2e6;
  --shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* Reset y base */
* {
  box-sizing: border-box;
}
body {
  ...;
}

/* Layout responsive */
.container {
  ...;
}
.row {
  ...;
}
.col {
  ...;
}

/* Componentes */
.btn {
  ...;
}
.card {
  ...;
}
.form-group {
  ...;
}
.nav {
  ...;
}

/* Chat específico */
.chat-container {
  ...;
}
.chat-message {
  ...;
}

/* Mobile-first media queries */
@media (max-width: 768px) {
  ...;
}
@media (max-width: 480px) {
  ...;
}
```

**Características**:

- Mobile-first design
- Flexbox/Grid layout
- Transiciones suaves
- Accesibilidad (ARIA labels)
- Dark mode toggle (opcional)

**Líneas estimadas**: +600

#### 7.2. Actualizar index.html

**Archivo**: `templates/index.html`

**Cambios**:

- Remover estilos inline
- Usar clases CSS de style.css
- Agregar meta viewport
- Mejorar estructura semántica HTML5
- Agregar favicon
- Responsive chat container
- Mejor UX en mobile (botones más grandes)

**Líneas estimadas**: +50 modificaciones

#### 7.3. Template Base

**Archivo**: `templates/base.html` (NUEVO)

**Contenido**:

```html
<!DOCTYPE html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{% block title %}{{ app_name }}{% endblock %}</title>
    <link rel="stylesheet" href="/static/style.css" />
    {% block extra_css %}{% endblock %}
  </head>
  <body>
    <nav class="navbar">
      <div class="container">
        <a href="/" class="brand">{{ app_name }}</a>
        <div class="nav-links">
          {% if current_user %}
          <span>{{ current_user.username }}</span>
          {% if current_user.is_admin %}
          <a href="/admin">Admin</a>
          {% endif %}
          <a href="/logout">Logout</a>
          {% else %}
          <a href="/login">Login</a>
          <a href="/register">Register</a>
          {% endif %}
        </div>
      </div>
    </nav>

    <main class="container">{% block content %}{% endblock %}</main>

    <footer>
      <p>&copy; 2025 {{ app_name }}</p>
    </footer>

    {% block extra_js %}{% endblock %}
  </body>
</html>
```

**Líneas estimadas**: +80

---

## Sprint M3.8: Sistema de Configuración Personalizable

### Objetivo

Permitir personalizar nombre app, nombre LLM, logo, colores.

### Tareas

#### 8.1. Base de Datos Configuración

**Archivo**: `app/db/config_db.py` (NUEVO)

**Tabla**:

```sql
CREATE TABLE app_config (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Valores por defecto
INSERT INTO app_config (key, value) VALUES
  ('app_name', 'LLM Chat'),
  ('llm_name', 'Assistant'),
  ('llm_personality', 'Soy un asistente inteligente llamado {llm_name}.'),
  ('primary_color', '#4a90e2'),
  ('logo_url', '/static/logo.png');
```

**Funciones**:

- `get_config(key: str) -> str`
- `set_config(key: str, value: str)`
- `get_all_config() -> dict`

**Líneas estimadas**: +80

#### 8.2. Backend API Configuración

**Archivo**: `app/api/routers/admin.py`

**Nuevos endpoints**:

```python
# Obtener configuración
GET /admin/config
Response: {
  "app_name": "LLM Chat",
  "llm_name": "Assistant",
  "llm_personality": "...",
  "primary_color": "#4a90e2",
  "logo_url": "/static/logo.png"
}

# Actualizar configuración
POST /admin/config
Body: {
  "app_name": "Mi Chat IA",
  "llm_name": "Jarvis",
  "primary_color": "#e74c3c"
}
Response: {"message": "Config updated"}

# Upload logo
POST /admin/config/logo
Content-Type: multipart/form-data
Response: {"logo_url": "/static/uploads/logo_abc123.png"}
```

**Líneas estimadas**: +90

#### 8.3. Frontend Panel Configuración

**Archivo**: `templates/admin_config.html`

**Componentes**:

- Form con inputs:
  - App Name (text)
  - LLM Name (text)
  - LLM Personality (textarea)
  - Primary Color (color picker)
  - Logo (file upload con preview)
- Botón "Save Changes"
- Preview en tiempo real

**Líneas estimadas**: +200

#### 8.4. Inyección Config en Templates

**Archivo**: `app/llm_client.py`

**Cambios**:

- Middleware para inyectar config en todos los templates
- `app_name`, `llm_name` disponibles en contexto
- CSS dinámico con variables color

```python
@app.context_processor
def inject_config():
    config = get_all_config()
    return {"app_name": config.get("app_name"), "llm_name": config.get("llm_name")}
```

**Líneas estimadas**: +20

#### 8.5. Personalidad LLM en Respuestas

**Archivo**: `app/api/routers/predict.py`

**Cambios**:

- Prepend system prompt con personalidad
- Usar `{llm_name}` en prompt

```python
llm_personality = get_config("llm_personality")
system_prompt = llm_personality.format(llm_name=get_config("llm_name"))
full_prompt = f"{system_prompt}\n\nUser: {user_prompt}\n{llm_name}:"
```

**Líneas estimadas**: +15

---

## Sprint M3.9: Navegación y Layout Admin Panel

### Objetivo

Crear estructura de navegación del panel admin.

### Tareas

#### 9.1. Layout Admin

**Archivo**: `templates/admin_layout.html` (NUEVO)

**Estructura**:

```html
{% extends "base.html" %} {% block content %}
<div class="admin-layout">
  <aside class="admin-sidebar">
    <nav class="admin-nav">
      <a
        href="/admin"
        class="nav-item {% if active=='dashboard' %}active{% endif %}"
      >
        <i class="icon-dashboard"></i> Dashboard
      </a>
      <a
        href="/admin/users"
        class="nav-item {% if active=='users' %}active{% endif %}"
      >
        <i class="icon-users"></i> Users
      </a>
      <a
        href="/admin/feedback"
        class="nav-item {% if active=='feedback' %}active{% endif %}"
      >
        <i class="icon-feedback"></i> Feedback
      </a>
      <a
        href="/admin/providers"
        class="nav-item {% if active=='providers' %}active{% endif %}"
      >
        <i class="icon-providers"></i> Providers
      </a>
      <a
        href="/admin/training"
        class="nav-item {% if active=='training' %}active{% endif %}"
      >
        <i class="icon-training"></i> Training
      </a>
      <a
        href="/admin/config"
        class="nav-item {% if active=='config' %}active{% endif %}"
      >
        <i class="icon-config"></i> Settings
      </a>
    </nav>
  </aside>

  <main class="admin-content">{% block admin_content %}{% endblock %}</main>
</div>
{% endblock %}
```

**Líneas estimadas**: +100

#### 9.2. CSS Admin Sidebar

**Archivo**: `static/admin.css` (NUEVO)

**Características**:

- Sidebar fijo en desktop
- Hamburger menu en mobile
- Transiciones suaves
- Active state
- Icons (Font Awesome o SVG)

**Líneas estimadas**: +250

#### 9.3. Rutas Admin

**Archivo**: `app/llm_client.py`

**Nuevas rutas**:

```python
@app.get("/admin", dependencies=[Depends(get_current_admin_user)])
async def admin_dashboard(request: Request):
    return templates.TemplateResponse("admin_stats.html", {...})

@app.get("/admin/users", dependencies=[Depends(get_current_admin_user)])
async def admin_users(request: Request):
    return templates.TemplateResponse("admin_users.html", {...})

# ... más rutas admin
```

**Líneas estimadas**: +60

---

## Arquitectura de Archivos M3

### Nuevos Archivos

```
app/
├── db/
│   └── config_db.py                    # Config personalizable (80 líneas)
├── api/routers/
│   └── admin.py                        # Extendido (+800 líneas)
└── admin_cli.py                        # Extendido (+80 líneas)

static/
├── style.css                           # CSS principal (600 líneas)
├── admin.css                           # CSS admin panel (250 líneas)
└── uploads/                            # Logos y archivos (directorio)

templates/
├── base.html                           # Template base (80 líneas)
├── admin_layout.html                   # Layout admin (100 líneas)
├── admin_users.html                    # Gestión usuarios (250 líneas)
├── admin_feedback.html                 # Gestión feedback (280 líneas)
├── admin_providers.html                # Gestión providers (220 líneas)
├── admin_stats.html                    # Dashboard métricas (300 líneas)
├── admin_training.html                 # Gestión training (350 líneas)
└── admin_config.html                   # Configuración (200 líneas)

doc/
└── M3_Diseño.md                        # Este archivo
```

### Archivos Modificados

```
app/
├── db/sqlite.py                        # +60 líneas (roles)
├── security/auth.py                    # +30 líneas (admin dependency)
├── api/routers/
│   └── auth.py                         # +15 líneas (primer admin)
└── llm_client.py                       # +80 líneas (rutas admin, config injection)

templates/
└── index.html                          # ~50 modificaciones (CSS classes)
```

---

## Resumen de Líneas de Código M3

### Nuevos Archivos

| Archivo                        | Líneas    |
| ------------------------------ | --------- |
| app/db/config_db.py            | 80        |
| static/style.css               | 600       |
| static/admin.css               | 250       |
| templates/base.html            | 80        |
| templates/admin_layout.html    | 100       |
| templates/admin_users.html     | 250       |
| templates/admin_feedback.html  | 280       |
| templates/admin_providers.html | 220       |
| templates/admin_stats.html     | 300       |
| templates/admin_training.html  | 350       |
| templates/admin_config.html    | 200       |
| **Total Nuevos**               | **2,710** |

### Archivos Modificados

| Archivo                  | Líneas Agregadas |
| ------------------------ | ---------------- |
| app/db/sqlite.py         | +60              |
| app/security/auth.py     | +30              |
| app/api/routers/auth.py  | +15              |
| app/api/routers/admin.py | +800             |
| app/admin_cli.py         | +80              |
| app/llm_client.py        | +80              |
| templates/index.html     | +50              |
| **Total Modificados**    | **+1,115**       |

### Total M3

**Nuevas líneas**: ~3,825  
**Archivos nuevos**: 11  
**Archivos modificados**: 7

---

## Prioridades de Implementación

### Fase 1: Fundamentos (Sprint M3.1 - M3.2)

1. ✅ Sistema de roles en DB
2. ✅ Primer usuario admin automático
3. ✅ CLI gestión roles
4. ✅ Backend API usuarios
5. ✅ Frontend panel usuarios

**Tiempo estimado**: 1-2 sesiones

### Fase 2: UI/UX Mejorada (Sprint M3.7 - M3.8)

1. ✅ CSS modular responsive
2. ✅ Template base
3. ✅ Actualizar index.html
4. ✅ Sistema configuración
5. ✅ Personalidad LLM

**Tiempo estimado**: 1-2 sesiones

### Fase 3: Gestión Contenido (Sprint M3.3 - M3.4)

1. ✅ Backend feedback
2. ✅ Frontend feedback
3. ✅ Backend providers
4. ✅ Frontend providers

**Tiempo estimado**: 1 sesión

### Fase 4: Analytics y Training (Sprint M3.5 - M3.6)

1. ✅ Backend métricas
2. ✅ Frontend dashboard
3. ✅ Backend training
4. ✅ Frontend training

**Tiempo estimado**: 2 sesiones

### Fase 5: Integración (Sprint M3.9)

1. ✅ Admin layout
2. ✅ Navegación
3. ✅ Testing completo
4. ✅ Documentación

**Tiempo estimado**: 1 sesión

---

## Consideraciones Técnicas

### Seguridad

- ✅ Todas las rutas admin protegidas con `Depends(get_current_admin_user)`
- ✅ Validación de archivos subidos (extensión, tamaño)
- ✅ Sanitización de inputs en configuración
- ✅ CSRF protection en forms
- ⚠️ Rate limiting en endpoints admin sensibles

### Performance

- ✅ Paginación en listados grandes (usuarios, feedback)
- ✅ Índices en columnas frecuentemente consultadas
- ✅ Lazy loading de gráficos
- ✅ Compresión de CSS/JS en producción
- ⚠️ Caché de configuración (Redis en futuro)

### UX

- ✅ Confirmaciones antes de acciones destructivas
- ✅ Mensajes de error claros
- ✅ Loading states en operaciones largas
- ✅ Responsive design mobile-first
- ✅ Accesibilidad (ARIA, keyboard navigation)

### Compatibilidad

- ✅ Chrome/Firefox/Safari/Edge últimas 2 versiones
- ✅ iOS Safari 12+
- ✅ Android Chrome 80+
- ✅ Degradación graceful en navegadores antiguos

---

## Tests M3 (Planificados)

### test_roles.py

- `test_first_user_is_admin()`
- `test_second_user_not_admin()`
- `test_grant_admin_permission()`
- `test_revoke_admin_permission()`
- `test_admin_only_endpoints_403()`

### test_admin_users.py

- `test_list_users()`
- `test_update_user_role()`
- `test_delete_user()`
- `test_reset_password()`

### test_admin_config.py

- `test_get_config()`
- `test_update_config()`
- `test_upload_logo()`
- `test_llm_personality_in_response()`

### test_admin_training.py

- `test_upload_training_file()`
- `test_start_training()`
- `test_training_status()`
- `test_cancel_training()`

### test_ui_responsive.py (E2E con Playwright)

- `test_mobile_navigation()`
- `test_admin_sidebar_mobile()`
- `test_chat_responsive()`

---

## Dependencias Nuevas M3

```txt
# Frontend (CDN - no pip)
# Font Awesome 6.4.0 (icons)
# Chart.js 4.4.0 (ya en M2)

# Backend
Pillow==10.1.0              # Procesamiento imágenes (logo upload)
python-multipart==0.0.6      # File uploads (ya existe)

# Tests E2E (opcional)
playwright==1.40.0
pytest-playwright==0.4.3
```

---

## Roadmap Visual M3

```
M3.1: Roles                 [████████] 100%
M3.2: Panel Usuarios        [████████] 100%
M3.3: Panel Feedback        [████████] 100%
M3.4: Panel Providers       [████████] 100%
M3.5: Panel Métricas        [████████] 100%
M3.6: Panel Training        [████████] 100%
M3.7: UI/UX Mejorada        [████████] 100%
M3.8: Config Personalizable [████████] 100%
M3.9: Admin Layout          [████████] 100%

Estado: 📋 EN DISEÑO → 🚧 EN DESARROLLO
```

---

## Criterios de Aceptación M3

### Funcionales

- [ ] Primer usuario registrado es admin automáticamente
- [ ] Admin puede otorgar/revocar permisos desde web y CLI
- [ ] Admin puede gestionar usuarios (ver, modificar rol, eliminar)
- [ ] Admin puede ver, filtrar y exportar feedback
- [ ] Admin puede cambiar provider y modelo desde web
- [ ] Admin puede ver métricas del sistema
- [ ] Admin puede subir archivos y ejecutar entrenamientos
- [ ] Admin puede personalizar nombre app y LLM
- [ ] LLM responde usando su nombre personalizado
- [ ] Interfaz responsive funciona en móviles

### No Funcionales

- [ ] Todas las rutas admin protegidas
- [ ] CSS modular separado de HTML
- [ ] Mobile-first design
- [ ] Accesible (WCAG 2.1 AA)
- [ ] Tests unitarios pasan
- [ ] Documentación actualizada

---

## Próximos Pasos Inmediatos

1. **Revisar y aprobar** este diseño M3
2. **Iniciar Sprint M3.1**: Sistema de roles
   - Modificar DB con columna `is_admin`
   - Implementar lógica primer usuario
   - Crear CLI comandos roles
3. **Iniciar Sprint M3.7**: CSS base
   - Crear `static/style.css`
   - Implementar mobile-first
   - Template base

¿Procedemos con la implementación? 🚀
