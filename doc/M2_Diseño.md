# M2 - Mejoras Post-M1: Seguridad, Despliegue y Características Avanzadas

## 1. Objetivo

Consolidar la arquitectura modular de M1 con mejoras de seguridad, configuración robusta, integración de proveedores externos (Claude/OpenAI), optimizaciones de rendimiento y funcionalidades avanzadas opcionales.

## 2. Estado Actual (Post-M1)

**Completado en M1:**

- Arquitectura modular (core, security, db, models, api/routers, providers, training).
- Logging estructurado JSON + request_id.
- Métricas básicas (/metrics con latencias, contadores, status codes).
- Rate limiting por IP/header.
- Autenticación JWT con cookies HttpOnly + SameSite.
- Tests unitarios (auth, predict, feedback, metrics, rate_limit).
- Trainer unificado con dataset multi-formato.
- Provider abstraction (HuggingFace base implementado).
- Configuración `.env` con SECRET_KEY externalizado.
- Versiones pinned en `requirements.txt`.

**✅ Completado en M2:**

- ✅ Sanitización feedback XSS con html.escape() + regex patterns
- ✅ Cookie Secure flag condicional a ENVIRONMENT=production
- ✅ datetime.utcnow → datetime.now(timezone.utc)
- ✅ Selección dispositivo GPU/CPU vía settings.DEVICE
- ✅ Migración a lifespan events (@asynccontextmanager)
- ✅ Pydantic Settings V2 completa con SettingsConfigDict
- ✅ Docker multi-stage (Dockerfile + docker-compose + docs)
- ✅ Provider Claude real con Anthropic API
- ✅ Provider OpenAI real con OpenAI API
- ✅ Integración providers en model_manager (switching dinámico)
- ✅ Cache LRU respuestas LLM (hash + TTL)
- ✅ Streaming tokens SSE (StreamingResponse + cliente JS)
- ✅ Embeddings + FAISS (sentence-transformers)
- ✅ Dashboard admin con Chart.js
- ✅ Métricas entrenamiento (SQLite + endpoints)

## 3. Sprints Planificados

### Sprint M2.1: Seguridad, Configuración y Despliegue ✅ COMPLETADO

| Item                          | Prioridad | Componente                | Estado        | Archivos Creados/Modificados                                     |
| ----------------------------- | --------- | ------------------------- | ------------- | ---------------------------------------------------------------- |
| Sanitización feedback XSS     | Alta      | `api/routers/feedback.py` | ✅ Completado | `feedback.py`, `test_feedback.py`                                |
| Cookie Secure flag            | Alta      | `llm_client.py`, `.env`   | ✅ Completado | `llm_client.py`, `.env.example`                                  |
| datetime.utcnow fix           | Alta      | `security/auth.py`        | ✅ Completado | `auth.py`                                                        |
| Selección dispositivo GPU/CPU | Media     | `models/model_manager.py` | ✅ Completado | `model_manager.py`, `settings.py`, `.env.example`                |
| Migrar a Lifespan events      | Media     | `main.py`                 | ✅ Completado | `main.py`                                                        |
| Pydantic Settings completa    | Media     | `core/settings.py`        | ✅ Completado | `settings.py`, routers, config                                   |
| Documentación Docker          | Media     | `doc/`, raíz              | ✅ Completado | `Dockerfile`, `docker-compose.yml`, `.dockerignore`, `README.md` |

### Sprint M2.2: Proveedores Externos ✅ COMPLETADO

| Item                  | Prioridad | Componente                | Estado        | Archivos Creados/Modificados |
| --------------------- | --------- | ------------------------- | ------------- | ---------------------------- |
| Provider Claude real  | Media     | `providers/claude.py`     | ✅ Completado | `claude.py`, `.env.example`  |
| Provider OpenAI real  | Media     | `providers/openai.py`     | ✅ Completado | `openai.py`, `.env.example`  |
| Integración providers | Media     | `models/model_manager.py` | ✅ Completado | `model_manager.py`           |

### Sprint M2.3: Optimización y Funcionalidades Avanzadas ✅ COMPLETADO

| Item                      | Prioridad | Componente               | Estado        | Archivos Creados/Modificados                                     |
| ------------------------- | --------- | ------------------------ | ------------- | ---------------------------------------------------------------- |
| Cache respuestas LLM      | Baja      | `core/cache.py`          | ✅ Completado | `cache.py`, `predict.py`                                         |
| Streaming tokens SSE      | Baja      | `api/routers/predict.py` | ✅ Completado | `predict.py`, `templates/index.html`                             |
| Métricas entrenamiento    | Baja      | `db/training_metrics.py` | ✅ Completado | `training_metrics.py`, `api/routers/training.py`                 |
| Embeddings + vector store | Opcional  | `models/embeddings.py`   | ✅ Completado | `embeddings.py`, `api/routers/embeddings.py`, `requirements.txt` |
| Dashboard admin           | Opcional  | `templates/admin.html`   | ✅ Completado | `admin.html`, `api/routers/admin.py`                             |

| Panel admin dashboard | Opcional | `templates/admin.html` | UI Chart.js para métricas; endpoint `/admin` protegido por rol. | `admin.html`, router admin |

## 4. Detalles Técnicos por Sprint

### M2.1: Seguridad y Configuración

**Sanitización Feedback:**

- Usar `html.escape()` o biblioteca `bleach` para limpiar entrada.
- Validar longitud y rechazar caracteres de control/binarios.
- Test: enviar `<script>alert('xss')</script>` y verificar escape o rechazo 400.

**Cookie Secure:**

```python
# app/llm_client.py
secure = os.getenv("ENVIRONMENT", "development") == "production"
response.set_cookie(..., secure=secure, httponly=True, samesite="lax")
```

**Lifespan Migration:**

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_feedback_db()
    init_user_db()
    load_model()
    yield
    # Cleanup si es necesario

app = FastAPI(lifespan=lifespan)
```

**Pydantic Settings:**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str
    DEVICE: str = "cpu"
    RATE_LIMIT_REQUESTS: int = 10
    ENVIRONMENT: str = "development"
    # ... todas las env vars

    class Config:
        env_file = ".env"

settings = Settings()
```

**Docker:**

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### M2.2: Proveedores Externos

**Claude Provider:**

```python
import httpx

class ClaudeProvider(BaseLLMProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1/messages"

    def generate(self, prompt: str, max_length: int = 100, **kwargs) -> str:
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}
        payload = {"model": "claude-3-sonnet-20240229", "max_tokens": max_length, "messages": [{"role": "user", "content": prompt}]}
        resp = httpx.post(self.base_url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]
```

**OpenAI Provider:** Similar estructura con `openai` SDK o requests directos.

**Test Switching:**

```python
def test_switch_to_claude(client):
    r = client.post("/model", json={"provider": "claude", "model": "claude-3-sonnet"})
    assert r.status_code == 200
    r_predict = client.post("/predict", json={"prompt": "Hola"})
    # Mock debe devolver texto esperado de Claude
```

### M2.3: Optimización

**Cache LRU:**

```python
from functools import lru_cache
import hashlib

cache = {}

def cache_key(prompt, params):
    return hashlib.sha256(f"{prompt}{params}".encode()).hexdigest()

def get_cached(key):
    return cache.get(key)

def set_cache(key, value, ttl=3600):
    cache[key] = {"value": value, "expires": time.time() + ttl}
```

**Streaming:**

```python
from fastapi.responses import StreamingResponse

async def generate_stream(prompt):
    for token in model.generate_tokens(prompt):
        yield f"data: {token}\n\n"

@router.post("/predict/stream")
async def predict_stream(req: PredictRequest):
    return StreamingResponse(generate_stream(req.prompt), media_type="text/event-stream")
```

## 5. Criterios de Aceptación

### M2.1

- [ ] Feedback con `<script>` rechazado o escapado en DB.
- [ ] Cookie `Secure=True` solo en producción (verificar header).
- [ ] Tests verdes sin warnings deprecation `on_event` y `utcnow`.
- [ ] Variable `DEVICE` funcional; modelo carga en GPU si disponible.
- [ ] `Settings` pydantic valida todas env vars; error claro si falta SECRET_KEY.
- [ ] `docker-compose up` levanta API funcional con volúmenes persistentes.

### M2.2

- [ ] `/predict` con `provider=claude` llama Anthropic API (mock test ok).
- [ ] `/predict` con `provider=openai` llama OpenAI API (mock test ok).
- [ ] Test switching cambia provider dinámicamente sin reinicio.

### M2.3

- [ ] Cache reduce latencia >50% en requests repetidos.
- [ ] Streaming tokens visible en cliente JS (EventSource).
- [ ] `/training/metrics` muestra gráfica loss histórico.
- [ ] `/embed` retorna embeddings 384-dim; búsqueda top-k funcional.
- [ ] Dashboard `/admin` renderiza métricas Chart.js.

## 6. Dependencias y Riesgos

**Dependencias Nuevas:**

- `bleach` (sanitización HTML).
- `httpx` o `anthropic` SDK.
- `openai` SDK.
- `redis` (cache opcional).
- `sentence-transformers`, `faiss-cpu` (embeddings).

**Riesgos:**

- API keys Claude/OpenAI requieren cuentas válidas (usar mocks en CI).
- GPU requiere drivers CUDA; Dockerfile debe soportar CPU-only por defecto.
- Streaming incrementa complejidad manejo errores.
- Vector store FAISS no thread-safe sin lock.

## 7. Próximos Pasos Post-M2

- **M3 (opcional):** Autenticación avanzada (OAuth2, roles granulares).
- **M4:** Monitoreo observabilidad (Prometheus exporters, Grafana).
- **M5:** Escalamiento horizontal (load balancer, modelo distribuido).

---

**Fecha de Inicio:** 20 noviembre 2025  
**Responsable:** Equipo LLM Modular  
**Revisión:** Post cada sprint
