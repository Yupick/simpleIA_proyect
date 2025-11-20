# simpleIA_proyect — LLM local primero (con soporte para nube)

Este proyecto implementa un sistema LLM modular con FastAPI y Hugging Face Transformers, diseñado con la filosofía local-first: su función principal es correr modelos en tu propia máquina, con la opción de integrar modelos hospedados en la nube mediante una capa de proveedores.

Características clave

- Local primero: ejecuta e infiere con modelos locales (CPU o GPU si disponible).
- Soporte multi-proveedor (en progreso): arquitectura preparada para integrar servicios externos (p. ej., Claude, OpenAI) sin cambiar el código de negocio.
- API modular: endpoints separados por dominio (auth, predict, model, feedback).
- Autenticación JWT y almacenamiento en SQLite.
- Feedback para reentrenamiento y entrenamiento unificado básico.
- Rate limiting simple para `/predict` configurable por entorno.

Estructura del proyecto (resumen)

- `config/`: configuración (`config.json`).
- `app/`: código de la aplicación (API modular, seguridad, modelo, DB, providers, training).
  - `app/main.py`: entrypoint de la API modular.
  - `app/api/routers/`: rutas `auth`, `predict`, `model`, `feedback`.
  - `app/models/`: gestor de modelo (`model_manager.py`).
  - `app/security/`: JWT y hashing.
  - `app/db/`: SQLite helpers.
  - `app/providers/`: abstracciones de proveedores (HF listo; externos en progreso).
  - `app/training/`: esqueleto de trainer unificado.
- `model_llm/`: checkpoints y modelos entrenados/locales.
- `templates/`: HTML para cliente web simple.
- `feedback/`: bases SQLite de usuarios y feedback.
- `requirements.txt`: dependencias.
- `run_llm.sh` / `setup_env.sh`: scripts de arranque y entorno.

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

- `SECRET_KEY`: cambia por un valor seguro.
- `DEFAULT_MODEL`: nombre o ruta local del modelo (p. ej., `gpt2` o `model_llm/mi_modelo_local`).
- `NUM_TRAIN_EPOCHS`, `TRAIN_BATCH_SIZE`: parámetros de entrenamiento por defecto.

2. `config/config.json` controla principalmente el modelo seleccionado en caliente:

```json
{
  "selected_model": "flax-community/gpt-2-spanish"
}
```

Puedes cambiarlo por una carpeta local guardada en `model_llm/`.

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
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Salud del servicio: `GET http://localhost:8000/health`

Endpoints principales

- `POST /auth/register`: registrar usuario. Body JSON `{ "username", "password" }` o `application/x-www-form-urlencoded` para `/auth/login`.
- `POST /auth/login`: login OAuth2 Password → `{ access_token, token_type }`.
- `GET /model`: modelo actual.
- `POST /model`: cambiar modelo `{ "model_name": "gpt2" }` (acepta ruta local o id HF). Recarga el modelo.
- `POST /predict`: inferencia `{ "prompt", "max_length", "num_return_sequences", "temperature" }`.
- `POST /feedback`: almacenar feedback `{ "text" }` (límite 5000 chars).

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

- Por defecto se usa Hugging Face local (`transformers.from_pretrained`). Si apuntas a una carpeta en `model_llm/`, se cargará desde disco.
- La capa `app/providers/` permite añadir proveedores externos. Ej.: un `ClaudeProvider` podría consumir un endpoint remoto con una API key definida en `.env`. La API enrutaría las solicitudes sin tocar tu lógica de negocio.

Entrenamiento local (básico)

- Opción 1 (legacy): usar `app/llm_trainer.py` existentes para flujos de fine-tuning con ficheros en `trainer_llm/`.
- Opción 2 (unificado en progreso): `app/training/trainer.py` expone una función `train(model_name, lines)` para integrar un pipeline más limpio. Los checkpoints se guardan en `model_llm/`; luego puedes seleccionarlos con `POST /model` indicando la ruta local.

Cliente web y CLI (opcionales)

- Cliente web simple: `app/llm_client.py` en puerto 8001. Requiere que la API esté corriendo en 8000. Nota: las rutas de auth del cliente legacy pueden diferir de las nuevas (`/auth/*`).
- CLI: `app/llm_client_line.py` para probar prompts rápidos contra `/predict`.

Seguridad

- Define `SECRET_KEY` en `.env` y usa HTTPS en producción (cookies seguras, SameSite, etc.).
- Agrega rate limiting/middleware anti-abuso si expones `/predict` públicamente.

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

- Memoria insuficiente al cargar modelos grandes: cambia `DEFAULT_MODEL`/`selected_model` por un modelo más pequeño (ej. `gpt2`), usa CPU o activa GPU si disponible.
- Dependencias: ejecuta `pip install -r requirements.txt` tras activar el entorno virtual.

Licencia
Integración futura Claude / OpenAI

- Añadirás un provider específico implementando la interfaz en `app/providers/`.
- Variables esperadas (ejemplos futuros): `CLAUDE_API_KEY`, `OPENAI_API_KEY`.
- Endpoint `/model` permitirá cambiar modelo/proveedor sin reiniciar.
- No especificada. Añade un archivo `LICENSE` si corresponde.
