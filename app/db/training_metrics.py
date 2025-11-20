"""
Base de datos para métricas de entrenamiento.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TRAINING_METRICS_DB = BASE_DIR / "feedback" / "training_metrics.sqlite"

def init_training_metrics_db():
    """Inicializa la base de datos de métricas de entrenamiento."""
    TRAINING_METRICS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(TRAINING_METRICS_DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS training_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT,
            total_epochs INTEGER,
            status TEXT DEFAULT 'running'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS epoch_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            epoch INTEGER NOT NULL,
            loss REAL,
            learning_rate REAL,
            timestamp TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES training_runs(id)
        )
    """)
    conn.commit()
    conn.close()
    logger.info(f"[TrainingMetrics] Database initialized at {TRAINING_METRICS_DB}")

def create_training_run(model_name: str, total_epochs: int) -> int:
    """
    Crea un nuevo registro de training run.
    
    Returns:
        ID del training run creado
    """
    conn = sqlite3.connect(TRAINING_METRICS_DB)
    c = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    c.execute("""
        INSERT INTO training_runs (model_name, start_time, total_epochs, status)
        VALUES (?, ?, ?, 'running')
    """, (model_name, now, total_epochs))
    run_id = c.lastrowid
    conn.commit()
    conn.close()
    logger.info(f"[TrainingMetrics] Created training run {run_id} for {model_name}")
    return run_id

def log_epoch_metrics(run_id: int, epoch: int, loss: float, learning_rate: float):
    """Registra métricas de un epoch."""
    conn = sqlite3.connect(TRAINING_METRICS_DB)
    c = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    c.execute("""
        INSERT INTO epoch_metrics (run_id, epoch, loss, learning_rate, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (run_id, epoch, loss, learning_rate, now))
    conn.commit()
    conn.close()
    logger.info(f"[TrainingMetrics] Logged epoch {epoch} for run {run_id}: loss={loss:.4f}")

def finish_training_run(run_id: int, status: str = "completed"):
    """Marca un training run como finalizado."""
    conn = sqlite3.connect(TRAINING_METRICS_DB)
    c = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    c.execute("""
        UPDATE training_runs
        SET end_time = ?, status = ?
        WHERE id = ?
    """, (now, status, run_id))
    conn.commit()
    conn.close()
    logger.info(f"[TrainingMetrics] Finished training run {run_id} with status: {status}")

def get_training_runs(limit: int = 10) -> List[Dict]:
    """Obtiene los últimos training runs."""
    conn = sqlite3.connect(TRAINING_METRICS_DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT * FROM training_runs
        ORDER BY start_time DESC
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_epoch_metrics(run_id: int) -> List[Dict]:
    """Obtiene las métricas de epochs para un training run."""
    conn = sqlite3.connect(TRAINING_METRICS_DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("""
        SELECT * FROM epoch_metrics
        WHERE run_id = ?
        ORDER BY epoch ASC
    """, (run_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_latest_run_metrics() -> Optional[Dict]:
    """Obtiene las métricas del último training run."""
    runs = get_training_runs(limit=1)
    if not runs:
        return None
    run = runs[0]
    epochs = get_epoch_metrics(run['id'])
    return {
        "run": run,
        "epochs": epochs
    }
