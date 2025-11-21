# simpleIA_proyect — LLM local primero (con soporte para nube)

Este proyecto implementa un sistema LLM modular con FastAPI y Hugging Face Transformers, diseñado con la filosofía local-first: su función principal es correr modelos en tu propia máquina, con la opción de integrar modelos hospedados en la nube mediante una capa de proveedores.

## Características M1 (Completado)

- ✅ **Local primero**: ejecuta e infiere con modelos locales (CPU o GPU si disponible)
- ✅ **API modular**: endpoints separados por dominio (auth, predict, model, feedback)
- ✅ **Autenticación JWT** y almacenamiento en SQLite
- ✅ **Feedback** para reentrenamiento
- ✅ **Rate limiting** simple para `/predict` configurable por entorno
- ✅ **Sanitización XSS** en feedback
- ✅ **Tests básicos**: autenticación, predicción, feedback, métricas

## Características M2 (Completado) 🚀

### Seguridad Mejorada

- ✅ **Cookies Secure** condicionales según `ENVIRONMENT` (production/development)
- ✅ **datetime.now(timezone.utc)** en lugar de utcnow deprecated
- ✅ **Sanitización XSS avanzada** con html.escape y regex

### Configuración Modernizada

- ✅ **Pydantic Settings V2** con SettingsConfigDict
- ✅ **Lifespan events** (@asynccontextmanager) reemplaza @on_event deprecated
- ✅ **Selección dispositivo** (CPU/CUDA) via settings.DEVICE

### Providers Multi-LLM

- ✅ **ClaudeProvider**: integración con Anthropic API usando httpx
- ✅ **OpenAIProvider**: integración con OpenAI API
- ✅ **HuggingFaceProvider**: local transformers
- ✅ **Switching dinámico** via config.provider (hf/claude/openai)

### Performance y Caché

- ✅ **Cache LRU** para respuestas LLM con TTL y hash SHA256
- ✅ **Streaming SSE**: StreamingResponse para tokens en tiempo real
- ✅ **Cache hit/miss tracking** con estadísticas

### Embeddings y Búsqueda Semántica

- ✅ **sentence-transformers**: modelo all-MiniLM-L6-v2 (384 dims)
- ✅ **FAISS vector store**: búsqueda L2 similarity
- ✅ **Endpoints /embed**: encode, add, search, save, load, stats
- ✅ **Persistencia**: save/load índice FAISS + documentos pickle

### Dashboard y Métricas

- ✅ **Dashboard admin**: Chart.js con gráficos de requests, latency, status, feedback
- ✅ **Métricas training**: SQLite para loss por epoch
- ✅ **Endpoints /training**: runs, metrics, latest
- ✅ **Auto-refresh** dashboard cada 30s

### Infraestructura

- ✅ **Docker completo**: Dockerfile multi-stage + docker-compose.yml
- ✅ **.dockerignore** optimizado
- ✅ **run_llm.sh mejorado**: comandos all/trainer/api/client/line/admin
- ✅ **admin_cli.py**: herramientas CLI (feedback list, model reload)
- ✅ **.gitignore completo**: modelos, embeddings, caches, notebooks

### Tests M2 (Creados)

- ✅ **test_providers.py**: ClaudeProvider, OpenAIProvider, initialization
- ✅ **test_cache.py**: LRU eviction, TTL, stats, hash collision
- ✅ **test_streaming.py**: SSE events, cache integration, error handling
- ✅ **test_embeddings.py**: encode, search, FAISS, endpoints
- ⚠️ **Nota**: Tests M2 requieren ajustes para coincidir con implementación real; tests M1 (7) pasan correctamente

Estructura del proyecto (resumen)

- `config/`: configuración (`config.json`)
- `app/`: código de la aplicación (API modular, seguridad, modelo, DB, providers, training)
  - `app/main.py`: entrypoint de la API modular con lifespan events
  - `app/api/routers/`: rutas `auth`, `predict`, `model`, `feedback`, `embeddings`, `admin`, `training`
  - `app/models/`: gestor de modelo (`model_manager.py`), embeddings (`embeddings.py`)
  - `app/security/`: JWT y hashing con get_current_user
  - `app/db/`: SQLite helpers (`sqlite.py`, `training_metrics.py`)
  - `app/providers/`: ClaudeProvider, OpenAIProvider, HuggingFaceProvider
  - `app/training/`: trainer unificado
  - `app/core/`: cache LRU, settings Pydantic V2, config, logging, metrics, rate_limit
- `model_llm/`: checkpoints y modelos entrenados/locales
- `templates/`: HTML para cliente web (index.html con streaming) y dashboard admin
- `feedback/`: bases SQLite de usuarios, feedback y métricas training
- `data/embeddings/`: índices FAISS y documentos
- `requirements.txt`: dependencias (numpy<2.0.0, sentence-transformers, faiss-cpu)
- `run_llm.sh`: script control servicios (all/trainer/api/client/line/admin)
- `Dockerfile` + `docker-compose.yml`: despliegue containerizado

Requisitos

- Python 3.10+ recomendado.
- pip reciente (`pip>=23`).
- Opcional: CUDA/cuDNN para acelerar inferencia/entrenamiento con PyTorch.

Instalación rápida

```bash
./setup_env.sh
# o manualmente
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Configuración (.env y config.json)

1. Copia el ejemplo y edítalo:

```bash
cp .env.example .env
```

Variables importantes:

- `SECRET_KEY`: cambia por un valor seguro (generado con `secrets.token_urlsafe(32)`)
- `ENVIRONMENT`: `development` o `production` (activa cookies Secure)
- `DEFAULT_MODEL`: nombre o ruta local del modelo (p. ej., `gpt2` o `model_llm/mi_modelo_local`)
- `DEVICE`: `cpu` o `cuda` (selección automática GPU si disponible)
- `ANTHROPIC_API_KEY`: API key para ClaudeProvider (opcional)
- `OPENAI_API_KEY`: API key para OpenAIProvider (opcional)
- `NUM_TRAIN_EPOCHS`, `TRAIN_BATCH_SIZE`: parámetros de entrenamiento por defecto

2. `config/config.json` controla principalmente el modelo seleccionado en caliente:

```json
{
  "selected_model": "flax-community/gpt-2-spanish",
  "provider": "hf"
}
```

Providers disponibles:

- `hf`: HuggingFace local (transformers)
- `claude`: Anthropic Claude API (requiere ANTHROPIC_API_KEY)
- `openai`: OpenAI API (requiere OPENAI_API_KEY)

Proveedor LLM

- Definir en `.env` o `config.json` la clave `LLM_PROVIDER` o `provider` (`hf` por defecto).
- Valores previstos futuros: `hf`, `claude`, `openai`, `custom`.
- Si no es `hf`, se usa por ahora el wrapper HuggingFace como placeholder (internamente igual, pero deja preparada la rama lógica).

Rate Limiting

- Variables de entorno:
  - `RATE_LIMIT_REQUESTS` (default 10)
  - `RATE_LIMIT_WINDOW_SECONDS` (default 60)
- Un bucket por IP cliente. Respuesta `429` si se excede.

Ejecutar (API modular local)

```bash
# Opción 1: Script run_llm.sh (recomendado)
./run_llm.sh all          # API + Cliente Web
./run_llm.sh api          # Solo API en :8000
./run_llm.sh client       # Solo Cliente Web en :8001
./run_llm.sh trainer      # Entrenador
./run_llm.sh line         # Cliente CLI
./run_llm.sh admin feedback  # Listar feedback
./run_llm.sh admin reload    # Recargar modelo

# Opción 2: Uvicorn directo
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Salud del servicio: `GET http://localhost:8000/health`

Endpoints principales

### Autenticación

- `POST /auth/register`: registrar usuario. Body JSON `{ "username", "password" }`
- `POST /auth/login`: login OAuth2 Password → `{ access_token, token_type }`

### Modelo

- `GET /model`: modelo actual y provider
- `POST /model`: cambiar modelo `{ "model_name": "gpt2" }` (acepta ruta local o id HF). Recarga el modelo

### Predicción

- `POST /predict`: inferencia `{ "prompt", "max_length", "num_return_sequences", "temperature", "stream": bool }`
  - `stream=false`: respuesta JSON completa
  - `stream=true`: StreamingResponse SSE (text/event-stream)

### Embeddings (M2)

- `POST /embed/encode`: generar embeddings `{ "texts": ["text1", "text2"] }`
- `POST /embed/add`: agregar documentos al índice `{ "documents": ["doc1", "doc2"] }`
- `POST /embed/search`: buscar similares `{ "query": "text", "k": 5 }`
- `POST /embed/save`: guardar índice FAISS
- `POST /embed/load`: cargar índice guardado
- `GET /embed/stats`: estadísticas del índice

### Dashboard y Métricas (M2)

- `GET /admin`: dashboard Chart.js (requiere autenticación)
- `GET /metrics`: métricas Prometheus-style
- `GET /training/runs`: listar runs de entrenamiento
- `GET /training/runs/{id}/metrics`: métricas de un run
- `GET /training/latest`: último run de entrenamiento

### Feedback

- `POST /feedback`: almacenar feedback `{ "text" }` (límite 5000 chars, sanitización XSS)

Ejemplos rápidos (curl)

```bash
# Registro
curl -X POST http://localhost:8000/auth/register \
	-H 'Content-Type: application/json' \
	-d '{"username":"demo","password":"demo123"}'

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
	-H 'Content-Type: application/x-www-form-urlencoded' \
	-d 'username=demo&password=demo123' | jq -r .access_token)

# Predicción (opcionalmente con token)
curl -X POST http://localhost:8000/predict \
	-H 'Content-Type: application/json' \
	-H "Authorization: Bearer $TOKEN" \
	-d '{"prompt":"Hola, ¿quién eres?","max_length":50}'

# Cambiar modelo (HF o carpeta local)
curl -X POST http://localhost:8000/model \
	-H 'Content-Type: application/json' \
	-d '{"model_name":"gpt2"}'
```

Local vs. nube (providers)

- **HuggingFace (hf)**: Modelos locales con `transformers.from_pretrained`. Si apuntas a carpeta en `model_llm/`, se carga desde disco.
- **Claude (claude)**: Integración con Anthropic API via httpx. Requiere `ANTHROPIC_API_KEY` en `.env`.
- **OpenAI (openai)**: Integración con OpenAI API via httpx. Requiere `OPENAI_API_KEY` en `.env`.

Cambiar provider en runtime:

```bash
# Via config.json
echo '{"selected_model":"gpt2","provider":"hf"}' > config/config.json

# O via admin CLI
./run_llm.sh admin reload
```

La arquitectura `app/providers/` permite añadir proveedores externos sin cambiar lógica de negocio.

Entrenamiento local (básico)

- Opción 1 (legacy): usar `app/llm_trainer.py` existentes para flujos de fine-tuning con ficheros en `trainer_llm/`.
- Opción 2 (unificado en progreso): `app/training/trainer.py` expone una función `train(model_name, lines)` para integrar un pipeline más limpio. Los checkpoints se guardan en `model_llm/`; luego puedes seleccionarlos con `POST /model` indicando la ruta local.

Cliente web y CLI

- **Cliente web**: `http://localhost:8001` - Interfaz HTML con streaming SSE, autenticación JWT via cookies
- **Cliente CLI**: `./run_llm.sh line` - Prompt interactivo contra `/predict`
- **Admin CLI**: `./run_llm.sh admin feedback|reload` - Herramientas administración

## Caché y Performance (M2)

### Cache LRU

- **Hash SHA256** de prompt+params como key
- **TTL configurable** (default 3600s)
- **Eviction LRU** al alcanzar max_size
- **Estadísticas**: hits, misses, hit_rate via `/metrics`

### Streaming SSE

- **Server-Sent Events** para tokens en tiempo real
- **Formato**: `data: <token>\n\n`
- **Cliente JS** con EventSource simulado
- **Cache bypass** automático en streaming

## Embeddings y Búsqueda (M2)

### Modelo

- **sentence-transformers/all-MiniLM-L6-v2**
- **384 dimensiones**
- **Normalización L2** automática

### FAISS Vector Store

- **IndexFlatL2** para búsqueda exhaustiva
- **Persistencia** a disco (.faiss + .pkl)
- **Add documents** con embeddings batch
- **Search** por similitud coseno/L2

### Casos de uso

- Búsqueda semántica en documentación
- RAG (Retrieval Augmented Generation)
- Similar questions matching
- Knowledge base search

Seguridad

- ✅ **SECRET_KEY** en `.env` - JWT signing
- ✅ **HTTPS** en producción - cookies seguras condicionales
- ✅ **Sanitización XSS** - html.escape + regex en feedback
- ✅ **Rate limiting** - configurable por entorno (default 10 req/60s)
- ✅ **Autenticación JWT** - tokens con expiración
- ✅ **CORS configurado** - origins permitidos via settings
- ⚠️ **Tokens en cookies** - SameSite=Lax, Secure en production
- ⚠️ **Validación inputs** - Pydantic models en todos los endpoints

Recomendaciones producción:

1. Generar SECRET_KEY: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
2. Set `ENVIRONMENT=production` en `.env`
3. Usar reverse proxy (nginx/traefik) con HTTPS
4. Rate limiting por IP en load balancer
5. Logs centralizados y monitoring

Notas de migración

- Se ha modularizado la API; `run_llm.sh` aún referencia el entrypoint legacy. Recomendado invocar `uvicorn app.main:app` directamente.
- Los trainers legacy seguirán disponibles mientras se completa la migración al trainer unificado.

## Despliegue con Docker

### Construcción y ejecución

```bash
# Construcción de imagen
docker build -t llm-modular-api .

# Ejecución simple
docker run -p 8000:8000 \
  -e SECRET_KEY="tu_clave_segura" \
  -v $(pwd)/feedback:/app/feedback \
  -v $(pwd)/model_llm:/app/model_llm \
  llm-modular-api

# Con docker-compose (recomendado)
docker-compose up -d
```

### Variables de entorno importantes

- `SECRET_KEY`: Clave para JWT (obligatoria en producción).
- `ENVIRONMENT`: `development` o `production` (activa cookies Secure).
- `DEVICE`: `cpu` o `cuda` (si GPU disponible).
- `DEFAULT_MODEL`: Modelo por defecto (puede ser ID HuggingFace o ruta local).
- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`: Para proveedores externos (opcional).

### Volúmenes persistentes

- `./feedback`: Bases de datos SQLite (usuarios, feedback).
- `./model_llm`: Modelos locales entrenados/personalizados.
- `huggingface_cache`: Cache de modelos descargados de HuggingFace.

### Acceso a servicios

- API: `http://localhost:8000`
- Cliente web: `http://localhost:8001` (si se levanta el servicio `llm-client`)
- Health check: `http://localhost:8000/health`
- Métricas: `http://localhost:8000/metrics`

### Producción

1. Generar SECRET_KEY seguro:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

2. Configurar `.env` con valores de producción.

3. Usar reverse proxy (nginx/traefik) con HTTPS.

4. Ajustar límites de recursos en `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: "2"
      memory: 4G
```

### Troubleshooting Docker

- **Error de permisos en volúmenes**: Asegurar que los directorios `feedback/` y `model_llm/` tengan permisos de escritura.
- **Modelo no carga**: Verificar que la variable `DEFAULT_MODEL` apunte a un modelo válido o que esté en cache.
- **GPU no detectada**: Instalar `nvidia-docker` y usar imagen base con CUDA.

Solución de problemas

### Memoria insuficiente

- Cambiar `DEFAULT_MODEL`/`selected_model` por modelo más pequeño (ej. `gpt2`)
- Usar `DEVICE=cpu` si GPU no disponible
- Reducir `TRAIN_BATCH_SIZE` en entrenamiento

### Dependencias

```bash
pip install -r requirements.txt
# Si falla NumPy/torch:
pip install "numpy<2.0.0" torch==2.2.1 --force-reinstall
```

### Provider switching no funciona

- Verificar `config/config.json` tiene `provider` correcto
- Reload modelo: `./run_llm.sh admin reload`
- Check logs: API key presente para claude/openai

### Embeddings lentos

- Primera ejecución descarga modelo (3GB)
- Cache en `~/.cache/torch/sentence_transformers/`
- Usar `DEVICE=cuda` si GPU disponible

### Tests fallan

```bash
# Tests M1 (deben pasar):
venv/bin/python -m pytest tests/test_auth.py tests/test_predict.py tests/test_feedback.py -v

# Tests M2 (requieren ajustes):
# Actualmente creados pero necesitan alinearse con implementación real
```

### Docker

- **Permisos volúmenes**: `chmod 777 feedback/ model_llm/`
- **GPU no detectada**: instalar nvidia-docker, usar imagen CUDA
- **Modelo no carga**: verificar DEFAULT_MODEL válido o en cache

## Próximos Pasos (M3 - Futuro)

- [ ] **Tests M2 completos**: ajustar test_providers.py, test_cache.py, test_streaming.py, test_embeddings.py
- [ ] **RAG Pipeline**: integración embeddings + retrieval + generation
- [ ] **Fine-tuning UI**: dashboard para entrenar modelos custom
- [ ] **Multi-model inference**: servir múltiples modelos simultáneamente
- [ ] **Async streaming**: mejorar performance con async generators
- [ ] **Prometheus metrics**: exportar métricas detalladas
- [ ] **WebSocket support**: alternativa a SSE para streaming
- [ ] **Model quantization**: GGUF, AWQ para modelos más ligeros
- [ ] **Kubernetes deployment**: Helm charts y manifests
- [ ] **CI/CD pipeline**: GitHub Actions para tests y deployment

## Licencia

No especificada. Añade un archivo `LICENSE` si corresponde.

## Contribuir

1. Fork el repositorio
2. Crear branch feature: `git checkout -b feature/amazing-feature`
3. Commit cambios: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Abrir Pull Request

## Changelog

### M2 (Noviembre 2025)

- ✅ Providers Claude/OpenAI integrados
- ✅ Cache LRU con TTL
- ✅ Streaming SSE
- ✅ Embeddings FAISS + sentence-transformers
- ✅ Dashboard admin Chart.js
- ✅ Docker production-ready
- ✅ Pydantic Settings V2
- ✅ Security hardening (XSS, cookies secure)

### M1 (Inicial)

- ✅ API modular FastAPI
- ✅ Autenticación JWT
- ✅ Rate limiting
- ✅ Feedback storage
- ✅ HuggingFace integration
- ✅ Tests básicos
