from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import os
import logging
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from .api.routers.predict import router as predict_router
from .api.routers.model import router as model_router
from .api.routers.feedback import router as feedback_router
from .api.routers.auth import router as auth_router
from .api.routers.metrics import router as metrics_router
from .api.routers.embeddings import router as embeddings_router
from .api.routers.admin import router as admin_router
from .api.routers.training import router as training_router
from .api.routers.user.products import router as products_router
from .api.routers.user.personal import router as personal_router
from .api.routers.user.chat import router as chat_router
from .api.routers.whatsapp import router as whatsapp_router
from .db.sqlite import init_feedback_db, init_user_db
from .db.training_metrics import init_training_metrics_db
from .db.products import init_products_db
from .db.personal import init_personal_db
from .db.conversations import init_conversations_db
from .models.model_manager import load_model
from .core.rate_limit import RateLimiter
from .core.logging import configure_logging, get_logger, request_id_var
from .core import metrics
from .core.metrics import LatencyTimer
from .core.settings import settings

rate_limiter = RateLimiter(requests=settings.RATE_LIMIT_REQUESTS, window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS)
configure_logging(json_mode=True, level=settings.LOG_LEVEL)
logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_feedback_db()
    init_user_db()
    init_training_metrics_db()
    init_products_db()
    init_personal_db()
    init_conversations_db()
    load_model()
    logger.info("Startup complete")
    yield
    # Shutdown (si es necesario limpiar recursos)


app = FastAPI(title="LLM Modular API", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def instrumentation_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or os.urandom(6).hex()
    request_id_var.set(request_id)
    # Normaliza la ruta para métricas (quita barra final excepto en raíz)
    raw_path = request.url.path
    path = raw_path if raw_path == "/" else raw_path.rstrip("/")
    metrics.record_request(path)
    timer = LatencyTimer()
    logger.info(f"Request {request.method} {path}")
    try:
        if path.startswith("/predict"):
            identifier = request.headers.get("X-Rate-Key") or ((request.client and request.client.host) or "unknown")
            if not rate_limiter.allow(identifier):
                response = JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
            else:
                response = await call_next(request)
        else:
            response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response
    finally:
        ms = timer.elapsed_ms()
        # Captura status code si se generó una respuesta
        try:
            status = response.status_code  # type: ignore[name-defined]
        except Exception:
            status = 500
        metrics.record_latency(path, ms)
        metrics.record_status(path, int(status))
        logger.info(f"Completed {request.method} {path} {ms:.2f}ms")
        request_id_var.set(None)

@app.get("/health")
async def health():
    return {"status": "ok"}

app.include_router(auth_router)
app.include_router(model_router)
app.include_router(predict_router)
app.include_router(feedback_router)
app.include_router(metrics_router)
app.include_router(embeddings_router)
app.include_router(admin_router)
app.include_router(training_router)
app.include_router(products_router, prefix="/api/user")
app.include_router(personal_router, prefix="/api/user")
app.include_router(chat_router, prefix="/api/user")
app.include_router(whatsapp_router, prefix="/api")
