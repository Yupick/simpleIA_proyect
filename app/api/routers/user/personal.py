"""
Routers para gestión de agenda personal del usuario (citas y tareas).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date
from app.security.auth import get_current_regular_user
from app.db import personal as personal_db

router = APIRouter(prefix="/personal", tags=["personal"])

# Inicializar DB al importar
personal_db.init_personal_db()


# === MODELS ===

class AppointmentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    start_datetime: str
    end_datetime: Optional[str] = None
    location: Optional[str] = None
    attendees: Optional[str] = None
    reminder_minutes: int = 15


class AppointmentUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    location: Optional[str] = None
    attendees: Optional[str] = None
    reminder_minutes: Optional[int] = None
    status: Optional[str] = None


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    due_date: Optional[str] = None
    priority: str = Field(default="medium", pattern="^(low|medium|high)$")
    category: Optional[str] = None
    reminder_minutes: int = 60


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = Field(None, pattern="^(low|medium|high)$")
    status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed)$")
    category: Optional[str] = None
    reminder_minutes: Optional[int] = None


# === APPOINTMENTS ENDPOINTS ===

@router.post("/appointments", status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment: AppointmentCreate,
    current_user: dict = Depends(get_current_regular_user)
):
    """Crea una nueva cita para el usuario actual."""
    appointment_id = personal_db.create_appointment(
        user_id=current_user["id"],
        title=appointment.title,
        description=appointment.description,
        start_datetime=appointment.start_datetime,
        end_datetime=appointment.end_datetime,
        location=appointment.location,
        attendees=appointment.attendees,
        reminder_minutes=appointment.reminder_minutes
    )
    return {"id": appointment_id, "message": "Cita creada exitosamente"}


@router.get("/appointments")
async def list_appointments(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_regular_user)
):
    """Lista todas las citas del usuario actual."""
    appointments = personal_db.list_appointments(
        user_id=current_user["id"],
        start_date=start_date,
        end_date=end_date,
        status=status
    )
    return appointments


@router.get("/appointments/count")
async def get_appointments_count(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_regular_user)
):
    """Obtiene el conteo de citas del usuario."""
    count = personal_db.get_appointments_count(current_user["id"], status)
    return {"count": count}


@router.get("/appointments/{appointment_id}")
async def get_appointment(
    appointment_id: int,
    current_user: dict = Depends(get_current_regular_user)
):
    """Obtiene una cita específica del usuario."""
    appointment = personal_db.get_appointment(appointment_id, current_user["id"])
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    return appointment


@router.put("/appointments/{appointment_id}")
async def update_appointment(
    appointment_id: int,
    appointment_update: AppointmentUpdate,
    current_user: dict = Depends(get_current_regular_user)
):
    """Actualiza una cita del usuario."""
    success = personal_db.update_appointment(
        appointment_id=appointment_id,
        user_id=current_user["id"],
        title=appointment_update.title,
        description=appointment_update.description,
        start_datetime=appointment_update.start_datetime,
        end_datetime=appointment_update.end_datetime,
        location=appointment_update.location,
        attendees=appointment_update.attendees,
        reminder_minutes=appointment_update.reminder_minutes,
        status=appointment_update.status
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    return {"message": "Cita actualizada exitosamente"}


@router.delete("/appointments/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_appointment(
    appointment_id: int,
    current_user: dict = Depends(get_current_regular_user)
):
    """Elimina una cita del usuario."""
    success = personal_db.delete_appointment(appointment_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cita no encontrada")
    return None


# === TASKS ENDPOINTS ===

@router.post("/tasks", status_code=status.HTTP_201_CREATED)
async def create_task(
    task: TaskCreate,
    current_user: dict = Depends(get_current_regular_user)
):
    """Crea una nueva tarea para el usuario actual."""
    task_id = personal_db.create_task(
        user_id=current_user["id"],
        title=task.title,
        description=task.description,
        due_date=task.due_date,
        priority=task.priority,
        category=task.category,
        reminder_minutes=task.reminder_minutes
    )
    return {"id": task_id, "message": "Tarea creada exitosamente"}


@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_regular_user)
):
    """Lista todas las tareas del usuario actual."""
    tasks = personal_db.list_tasks(
        user_id=current_user["id"],
        status=status,
        priority=priority,
        category=category
    )
    return tasks


@router.get("/tasks/count")
async def get_tasks_count(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_regular_user)
):
    """Obtiene el conteo de tareas del usuario."""
    count = personal_db.get_tasks_count(current_user["id"], status)
    return {"count": count}


@router.get("/tasks/categories")
async def get_task_categories(current_user: dict = Depends(get_current_regular_user)):
    """Obtiene todas las categorías de tareas del usuario."""
    return personal_db.get_task_categories(current_user["id"])


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: int,
    current_user: dict = Depends(get_current_regular_user)
):
    """Obtiene una tarea específica del usuario."""
    task = personal_db.get_task(task_id, current_user["id"])
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")
    return task


@router.put("/tasks/{task_id}")
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    current_user: dict = Depends(get_current_regular_user)
):
    """Actualiza una tarea del usuario."""
    success = personal_db.update_task(
        task_id=task_id,
        user_id=current_user["id"],
        title=task_update.title,
        description=task_update.description,
        due_date=task_update.due_date,
        priority=task_update.priority,
        status=task_update.status,
        category=task_update.category,
        reminder_minutes=task_update.reminder_minutes
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")
    return {"message": "Tarea actualizada exitosamente"}


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: dict = Depends(get_current_regular_user)
):
    """Elimina una tarea del usuario."""
    success = personal_db.delete_task(task_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")
    return None
