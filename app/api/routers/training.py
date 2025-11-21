"""
Router para métricas de entrenamiento.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Dict, Optional
from ...db.training_metrics import (
    get_training_runs,
    get_epoch_metrics,
    get_latest_run_metrics
)

router = APIRouter(prefix="/training", tags=["training"])

@router.get("/runs")
async def list_training_runs(limit: int = 10) -> List[Dict]:
    """Lista los últimos training runs."""
    try:
        return get_training_runs(limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching training runs: {e}")

@router.get("/runs/{run_id}/metrics")
async def get_run_metrics(run_id: int) -> Dict:
    """Obtiene las métricas de un training run específico."""
    try:
        epochs = get_epoch_metrics(run_id)
        if not epochs:
            raise HTTPException(status_code=404, detail="Training run not found")
        return {
            "run_id": run_id,
            "epochs": epochs
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching metrics: {e}")

@router.get("/latest")
async def get_latest_metrics() -> Optional[Dict]:
    """Obtiene las métricas del último training run."""
    try:
        result = get_latest_run_metrics()
        if result is None:
            raise HTTPException(status_code=404, detail="No training runs found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching latest metrics: {e}")
