"""
Router para gestión de entrenamiento de modelos LLM.
Incluye: subida de archivos, listado, eliminación, inicio de entrenamiento y monitoreo.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional
from pathlib import Path
from pydantic import BaseModel

from ...db.training_metrics import (
    get_training_runs,
    get_epoch_metrics,
    get_latest_run_metrics
)
from ...training.data_loader import TrainingDataLoader
from ...training.trainer import LLMTrainer
from ...training.job_manager import job_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/training", tags=["training"])

# Inicializar data loader
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
data_loader = TrainingDataLoader(BASE_DIR)
MODEL_DIR = BASE_DIR / "model_llm"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


# ===== MODELOS PYDANTIC =====

class TrainingConfig(BaseModel):
    """Configuración de entrenamiento."""
    model_name: str
    epochs: int = 3
    batch_size: int = 4
    learning_rate: float = 5e-5
    max_length: int = 128
    source: str = "all"  # 'all', 'dialogue', 'knowledge', o nombre de archivo
    folder: Optional[str] = None  # Para source específico de archivo


# ===== ENDPOINTS ARCHIVOS =====

@router.get("/files/{folder}")
async def list_files(folder: str) -> List[Dict]:
    """
    Lista archivos en una carpeta de entrenamiento.
    
    Args:
        folder: 'dialogue' o 'knowledge'
    """
    if folder not in ["dialogue", "knowledge"]:
        raise HTTPException(status_code=400, detail="Folder must be 'dialogue' or 'knowledge'")
    
    try:
        files = data_loader.list_files(folder)
        return files
    except Exception as e:
        logger.error(f"Error listing files in {folder}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/{folder}")
async def upload_file(folder: str, file: UploadFile = File(...)) -> Dict:
    """
    Sube un archivo a una carpeta de entrenamiento.
    
    Args:
        folder: 'dialogue' o 'knowledge'
        file: Archivo a subir
    """
    if folder not in ["dialogue", "knowledge"]:
        raise HTTPException(status_code=400, detail="Folder must be 'dialogue' or 'knowledge'")
    
    try:
        # Leer contenido
        content = await file.read()
        
        # Guardar archivo
        saved_path = data_loader.save_uploaded_file(folder, file.filename, content)
        
        return {
            "message": f"File uploaded successfully to {folder}",
            "filename": file.filename,
            "size": len(content),
            "path": str(saved_path)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/files/{folder}/{filename}")
async def delete_file(folder: str, filename: str) -> Dict:
    """
    Elimina un archivo de una carpeta de entrenamiento.
    
    Args:
        folder: 'dialogue' o 'knowledge'
        filename: Nombre del archivo a eliminar
    """
    if folder not in ["dialogue", "knowledge"]:
        raise HTTPException(status_code=400, detail="Folder must be 'dialogue' or 'knowledge'")
    
    try:
        data_loader.delete_file(folder, filename)
        return {
            "message": f"File {filename} deleted successfully from {folder}"
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"File {filename} not found in {folder}")
    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===== ENDPOINTS MODELOS =====

@router.get("/models/available")
async def get_available_models() -> Dict:
    """Retorna lista de modelos base disponibles para entrenar."""
    models_by_category = LLMTrainer.get_available_models()
    
    # Aplanar la estructura para el frontend
    all_models = []
    for category, models in models_by_category.items():
        all_models.extend([m["name"] for m in models])
    
    return {"models": all_models, "models_detailed": models_by_category}


# ===== ENDPOINTS ENTRENAMIENTO =====

def run_training_job(job_id: str, model_name: str, training_data: List[str], config: dict):
    """
    Función que ejecuta el entrenamiento (se ejecuta en background).
    
    Args:
        job_id: ID del trabajo
        model_name: Nombre del modelo base
        training_data: Datos de entrenamiento
        config: Configuración
    """
    try:
        # Crear entrenador
        trainer = LLMTrainer(
            model_name=model_name,
            training_data=training_data,
            output_dir=MODEL_DIR,
            config=config
        )
        
        # Callback de progreso
        def progress_callback(epoch, loss, step, total_steps):
            job_manager.update_progress(job_id, epoch, loss, step, total_steps)
        
        trainer.set_progress_callback(progress_callback)
        
        # Entrenar
        output_path = trainer.train()
        
        return output_path
        
    except Exception as e:
        logger.exception(f"Error in training job {job_id}")
        raise


@router.post("/start")
async def start_training(
    config: TrainingConfig,
    background_tasks: BackgroundTasks
) -> Dict:
    """
    Inicia un trabajo de entrenamiento en background.
    
    Args:
        config: Configuración del entrenamiento
    """
    try:
        # Recopilar datos según source
        if config.source == "all":
            training_data, stats = data_loader.collect_all_data()
            if not training_data:
                raise HTTPException(
                    status_code=400,
                    detail="No training data found in dialogue or knowledge folders"
                )
        
        elif config.source in ["dialogue", "knowledge"]:
            directory = data_loader.dialogue_dir if config.source == "dialogue" else data_loader.knowledge_dir
            training_data, _, _ = data_loader.collect_from_directory(directory)
            if not training_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"No training data found in {config.source} folder"
                )
        
        elif config.folder and config.source:
            # Entrenar con un archivo específico
            training_data = data_loader.collect_from_file(config.folder, config.source)
            if not training_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"No data found in file {config.source}"
                )
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid source configuration"
            )
        
        # Crear job
        job_config = {
            "epochs": config.epochs,
            "batch_size": config.batch_size,
            "learning_rate": config.learning_rate,
            "max_length": config.max_length
        }
        
        job_id = job_manager.create_job(
            model_name=config.model_name,
            config=job_config,
            data_lines=len(training_data)
        )
        
        # Iniciar entrenamiento en background
        job_manager.start_job(
            job_id,
            run_training_job,
            job_id,
            config.model_name,
            training_data,
            job_config
        )
        
        logger.info(f"Training job {job_id} started")
        
        return {
            "job_id": job_id,
            "message": "Training started successfully",
            "data_lines": len(training_data),
            "config": job_config
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting training: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> Dict:
    """
    Obtiene el estado de un trabajo de entrenamiento.
    
    Args:
        job_id: ID del trabajo
    """
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job.to_dict()


@router.get("/jobs")
async def list_jobs(limit: int = 10) -> List[Dict]:
    """Lista los últimos trabajos de entrenamiento."""
    return job_manager.list_jobs(limit)


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str) -> Dict:
    """
    Cancela un trabajo de entrenamiento en ejecución.
    
    Args:
        job_id: ID del trabajo
    """
    success = job_manager.cancel_job(job_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or not running")
    
    return {"message": "Job cancelled successfully"}


# ===== ENDPOINTS MÉTRICAS (legacy) =====

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
