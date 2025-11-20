# M1 - Diseño Arquitectura Modular y Plan de Mejoras

## 1. Objetivo

Estandarizar y modularizar el proyecto LLM para mejorar mantenibilidad, seguridad, escalabilidad y capacidad de extensión a proveedores externos (ej. Claude, OpenAI, etc.).

## 2. Estado Actual (Resumen)

- API monolítica en `app/llm_api.py` con estado global de modelo.
- Múltiples scripts de entrenamiento duplicados (`llm_trainer*.py`).
- Mezcla de responsabilidades (auth, feedback, modelo, predicción) en un solo archivo.
- Configuración estática y clave JWT embebida.

## 3. Arquitectura Objetivo (Capas)

| Capa            | Directorio        | Responsabilidad                         | Mapping desde código viejo                 |
| --------------- | ----------------- | --------------------------------------- | ------------------------------------------ |
| Core Config     | `app/core`        | Lectura y acceso a configuración        | Parte de `llm_api.py` y `llm_trainer*.py`  |
| Seguridad/Auth  | `app/security`    | Hash, JWT, extracción usuario actual    | Lógica en `llm_api.py`                     |
| Persistencia/DB | `app/db`          | Inicialización y operaciones SQLite     | Código disperso en `llm_api.py` y trainers |
| Manejo Modelo   | `app/models`      | Carga y generación thread-safe          | Globales en `llm_api.py`                   |
| Routers API     | `app/api/routers` | Endpoints separados por dominio         | Un solo archivo `llm_api.py`               |
| Providers       | `app/providers`   | Abstracción para múltiples LLM backends | No existía                                 |
| Entrenamiento   | `app/training`    | Lógica unificada fine-tuning            | Tres scripts duplicados                    |

## 4. Flujo de Solicitud (Nuevo)

1. Cliente invoca `/predict`.
2. Router `predict` valida input y llama a `models.model_manager.generate`.
3. `model_manager` asegura modelo cargado y genera texto.
4. Respuesta estructurada regresa al cliente.
5. Feedback pasa por `/feedback` con validación de longitud y se almacena vía `db.sqlite.store_feedback`.

## 5. Prioridades de Mejora

### Alta

- Externalizar SECRET_KEY y parámetros a variables de entorno (`.env`).
- Unificación trainer (eliminar duplicación y comportamiento divergente).
- Rate limiting y validación adicional en `/predict` (mitigar abuso).
- Sanitización/Límites feedback (máx 5000 chars, sin binarios).
- Pin de versiones críticas (`fastapi`, `transformers`, `torch`).
- Cookies seguras (`Secure`, `HttpOnly`, `SameSite=Lax`).

### Media

- Provider abstraction (Claude/OpenAI/HF).
- Logging estructurado (JSON + request ID).
- Métricas `/metrics` (Prometheus).
- Test unitarios básicos (auth, predict, feedback).
- Modo de carga lazy del modelo + selección dispositivo (GPU/CPU).

### Baja

- Refactor script `run_llm.sh` para soportar nuevo entrypoint `app.main:app`.
- Agregar documentación de despliegue en contenedor.
- Separar config en `config.yaml` con validación pydantic.
- CLI para administración (listar feedback, forzar recarga modelo).

### Opcionales

- Streaming de tokens (Server-Sent Events / websockets).
- Cache de respuestas con TTL.
- Embeddings y memoria contextual.
- Integración vector store (FAISS, Chroma).
- Panel admin ligero (dashboard).

## 6. Archivos Nuevos (M1)

- `app/core/config.py` (gestión configuración).
- `app/security/auth.py` (autenticación).
- `app/db/sqlite.py` (persistencia).
- `app/models/model_manager.py` (carga + generación).
- Routers: `predict.py`, `model.py`, `feedback.py`, `auth.py`.
- `app/main.py` (entrypoint modular).
- Providers: `base.py`, `huggingface.py`.
- Entrenamiento unificado: `training/trainer.py`.
- Documento diseño: `doc/M1_Diseño.md`.

## 7. Migración Progresiva

1. Mantener `llm_api.py` operativo para continuidad.
2. Validar nuevo `app/main.py` en puerto alterno para pruebas.
3. Actualizar script run para usar nuevo entrypoint cuando estable.
4. Depurar y remover trainers antiguos tras confirmación.

## 8. Estrategia de Tests Iniciales

- Mock de modelo (clase simple) para probar `/predict` sin cargar pesos reales.
- Test de registro + login y obtención de token.
- Test de feedback (verifica límite y almacenamiento).

## 9. Integración de Proveedores Externos (Visión)

Interfaz `BaseLLMProvider` permite añadir `ClaudeProvider` (API key + endpoint). Selección vía config: `{ "provider": "hf", "model": "gpt2" }`. Router `/model` gestiona cambio y recarga.

## 10. Próximos Pasos Sugeridos

- Añadir archivo `.env.example` + lectura con `python-dotenv`.
- Implementar tests base.
- Ajustar script de ejecución.
- Añadir validación pydantic a configuración ampliada.

---

Fin documento M1.
