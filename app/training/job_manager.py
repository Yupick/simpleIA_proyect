"""
Job Manager - Gestión de trabajos de entrenamiento en background.
"""

import uuid
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Estados de un trabajo de entrenamiento."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TrainingJob:
    """Representa un trabajo de entrenamiento."""
    
    def __init__(
        self,
        job_id: str,
        model_name: str,
        config: Dict,
        data_lines: int
    ):
        self.job_id = job_id
        self.model_name = model_name
        self.config = config
        self.data_lines = data_lines
        self.status = JobStatus.PENDING
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None
        self.progress = 0.0
        self.current_epoch = 0
        self.total_epochs = config.get("epochs", 3)
        self.current_loss = 0.0
        self.logs: list = []
    
    def to_dict(self) -> Dict:
        """Convierte el job a diccionario."""
        return {
            "job_id": self.job_id,
            "model_name": self.model_name,
            "config": self.config,
            "data_lines": self.data_lines,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "progress": self.progress,
            "current_epoch": self.current_epoch,
            "total_epochs": self.total_epochs,
            "current_loss": self.current_loss,
            "logs": self.logs[-50:]  # Últimos 50 logs
        }


class TrainingJobManager:
    """Gestiona trabajos de entrenamiento en background."""
    
    def __init__(self):
        self.jobs: Dict[str, TrainingJob] = {}
        self.active_jobs: Dict[str, asyncio.Task] = {}
    
    def create_job(
        self,
        model_name: str,
        config: Dict,
        data_lines: int
    ) -> str:
        """
        Crea un nuevo trabajo de entrenamiento.
        
        Args:
            model_name: Nombre del modelo a entrenar
            config: Configuración del entrenamiento
            data_lines: Número de líneas de datos
            
        Returns:
            ID del trabajo creado
        """
        job_id = str(uuid.uuid4())
        job = TrainingJob(job_id, model_name, config, data_lines)
        self.jobs[job_id] = job
        
        logger.info(f"Created training job {job_id} for model {model_name}")
        return job_id
    
    def get_job(self, job_id: str) -> Optional[TrainingJob]:
        """Obtiene un trabajo por su ID."""
        return self.jobs.get(job_id)
    
    def list_jobs(self, limit: int = 10) -> list:
        """Lista los últimos trabajos."""
        jobs = sorted(
            self.jobs.values(),
            key=lambda x: x.created_at,
            reverse=True
        )
        return [job.to_dict() for job in jobs[:limit]]
    
    def update_progress(
        self,
        job_id: str,
        epoch: int,
        loss: float,
        step: int,
        total_steps: int
    ):
        """Actualiza el progreso de un trabajo."""
        job = self.jobs.get(job_id)
        if not job:
            return
        
        # Epoch comienza en 0, pero para usuario mostramos desde 1
        display_epoch = max(1, epoch + 1)
        job.current_epoch = display_epoch
        job.current_loss = loss
        
        # Calcular progreso basado en steps totales
        if total_steps > 0:
            job.progress = min(100.0, (step / total_steps) * 100)
        
        log_entry = f"Epoch {display_epoch}/{job.total_epochs} - Step {step}/{total_steps} - Loss: {loss:.4f}"
        job.logs.append(log_entry)
        
        logger.info(f"Job {job_id}: {log_entry}")
    
    def mark_running(self, job_id: str):
        """Marca un trabajo como en ejecución."""
        job = self.jobs.get(job_id)
        if job:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now()
            logger.info(f"Job {job_id} started")
    
    def mark_completed(self, job_id: str, output_path: str):
        """Marca un trabajo como completado."""
        job = self.jobs.get(job_id)
        if job:
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()
            job.progress = 100.0
            job.logs.append(f"✓ Training completed. Model saved at: {output_path}")
            logger.info(f"Job {job_id} completed successfully")
    
    def mark_failed(self, job_id: str, error: str):
        """Marca un trabajo como fallido."""
        job = self.jobs.get(job_id)
        if job:
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now()
            job.error = str(error)
            job.logs.append(f"✗ Training failed: {error}")
            logger.error(f"Job {job_id} failed: {error}")
    
    async def run_job_async(
        self,
        job_id: str,
        train_func: Callable,
        *args,
        **kwargs
    ):
        """
        Ejecuta un trabajo de entrenamiento de forma asíncrona.
        
        Args:
            job_id: ID del trabajo
            train_func: Función de entrenamiento a ejecutar
            *args, **kwargs: Argumentos para train_func
        """
        try:
            self.mark_running(job_id)
            
            # Ejecutar entrenamiento en un executor para no bloquear
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, train_func, *args, **kwargs)
            
            if result:
                self.mark_completed(job_id, result)
            else:
                self.mark_failed(job_id, "Training returned no result")
                
        except Exception as e:
            self.mark_failed(job_id, str(e))
            logger.exception(f"Error in training job {job_id}")
        
        finally:
            # Limpiar task activo
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]
    
    def start_job(
        self,
        job_id: str,
        train_func: Callable,
        *args,
        **kwargs
    ) -> asyncio.Task:
        """
        Inicia la ejecución de un trabajo en background.
        
        Args:
            job_id: ID del trabajo
            train_func: Función de entrenamiento
            *args, **kwargs: Argumentos para train_func
            
        Returns:
            Task de asyncio
        """
        task = asyncio.create_task(
            self.run_job_async(job_id, train_func, *args, **kwargs)
        )
        self.active_jobs[job_id] = task
        return task
    
    def cancel_job(self, job_id: str) -> bool:
        """
        Cancela un trabajo en ejecución.
        
        Args:
            job_id: ID del trabajo
            
        Returns:
            True si se canceló exitosamente
        """
        if job_id in self.active_jobs:
            task = self.active_jobs[job_id]
            task.cancel()
            
            job = self.jobs.get(job_id)
            if job:
                job.status = JobStatus.CANCELLED
                job.completed_at = datetime.now()
                job.logs.append("✗ Training cancelled by user")
            
            logger.info(f"Job {job_id} cancelled")
            return True
        
        return False


# Instancia global del job manager
job_manager = TrainingJobManager()
