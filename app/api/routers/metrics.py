from fastapi import APIRouter
from ...core import metrics
from ...models import model_manager

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/")
def get_metrics():
    snap = metrics.snapshot()
    model_name = model_manager.current_model_name()
    return {
        **snap,
        "model_loaded": model_name is not None,
        "model_name": model_name,
    }
