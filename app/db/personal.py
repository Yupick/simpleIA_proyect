"""
Gestión de base de datos para agenda personal (citas y tareas).
Cada usuario tiene su propia agenda aislada.
"""
from pathlib import Path
import sqlite3
from typing import Optional, List
from datetime import datetime, date

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FEEDBACK_DIR = BASE_DIR / "feedback"
PERSONAL_DB_PATH = FEEDBACK_DIR / "personal.sqlite"

FEEDBACK_DIR.mkdir(exist_ok=True)

def init_personal_db():
    """Inicializa la base de datos de agenda personal con aislamiento por usuario."""
    with sqlite3.connect(str(PERSONAL_DB_PATH)) as conn:
        cursor = conn.cursor()
        
        # Tabla de citas/appointments
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                start_datetime TIMESTAMP NOT NULL,
                end_datetime TIMESTAMP,
                location TEXT,
                attendees TEXT,
                reminder_minutes INTEGER DEFAULT 15,
                status TEXT DEFAULT 'scheduled',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Tabla de tareas/tasks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                due_date DATE,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'pending',
                category TEXT,
                reminder_minutes INTEGER DEFAULT 60,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Índices para búsquedas rápidas
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_appointments_user_id 
            ON appointments(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_appointments_datetime 
            ON appointments(user_id, start_datetime)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_user_id 
            ON tasks(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_due_date 
            ON tasks(user_id, due_date)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_status 
            ON tasks(user_id, status)
        """)
        
        conn.commit()


# === APPOINTMENTS ===

def create_appointment(
    user_id: int,
    title: str,
    start_datetime: str,
    end_datetime: str = None,
    description: str = None,
    location: str = None,
    attendees: str = None,
    reminder_minutes: int = 15
) -> int:
    """Crea una nueva cita para un usuario."""
    with sqlite3.connect(str(PERSONAL_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO appointments 
            (user_id, title, description, start_datetime, end_datetime, location, attendees, reminder_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, title, description, start_datetime, end_datetime, location, attendees, reminder_minutes))
        conn.commit()
        return cursor.lastrowid


def get_appointment(appointment_id: int, user_id: int) -> Optional[dict]:
    """Obtiene una cita por ID, verificando que pertenezca al usuario."""
    with sqlite3.connect(str(PERSONAL_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, title, description, start_datetime, end_datetime, 
                   location, attendees, reminder_minutes, status, created_at, updated_at
            FROM appointments
            WHERE id = ? AND user_id = ?
        """, (appointment_id, user_id))
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "user_id": row[1],
                "title": row[2],
                "description": row[3],
                "start_datetime": row[4],
                "end_datetime": row[5],
                "location": row[6],
                "attendees": row[7],
                "reminder_minutes": row[8],
                "status": row[9],
                "created_at": row[10],
                "updated_at": row[11]
            }
        return None


def list_appointments(
    user_id: int,
    start_date: str = None,
    end_date: str = None,
    status: str = None
) -> List[dict]:
    """Lista las citas de un usuario con filtros opcionales."""
    with sqlite3.connect(str(PERSONAL_DB_PATH)) as conn:
        cursor = conn.cursor()
        
        query = """
            SELECT id, user_id, title, description, start_datetime, end_datetime,
                   location, attendees, reminder_minutes, status, created_at, updated_at
            FROM appointments
            WHERE user_id = ?
        """
        params = [user_id]
        
        if start_date:
            query += " AND start_datetime >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND start_datetime <= ?"
            params.append(end_date)
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY start_datetime ASC"
        
        cursor.execute(query, params)
        appointments = []
        for row in cursor.fetchall():
            appointments.append({
                "id": row[0],
                "user_id": row[1],
                "title": row[2],
                "description": row[3],
                "start_datetime": row[4],
                "end_datetime": row[5],
                "location": row[6],
                "attendees": row[7],
                "reminder_minutes": row[8],
                "status": row[9],
                "created_at": row[10],
                "updated_at": row[11]
            })
        return appointments


def update_appointment(
    appointment_id: int,
    user_id: int,
    title: str = None,
    description: str = None,
    start_datetime: str = None,
    end_datetime: str = None,
    location: str = None,
    attendees: str = None,
    reminder_minutes: int = None,
    status: str = None
) -> bool:
    """Actualiza una cita, verificando que pertenezca al usuario."""
    with sqlite3.connect(str(PERSONAL_DB_PATH)) as conn:
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if start_datetime is not None:
            updates.append("start_datetime = ?")
            params.append(start_datetime)
        if end_datetime is not None:
            updates.append("end_datetime = ?")
            params.append(end_datetime)
        if location is not None:
            updates.append("location = ?")
            params.append(location)
        if attendees is not None:
            updates.append("attendees = ?")
            params.append(attendees)
        if reminder_minutes is not None:
            updates.append("reminder_minutes = ?")
            params.append(reminder_minutes)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        
        if not updates:
            return False
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([appointment_id, user_id])
        
        query = f"UPDATE appointments SET {', '.join(updates)} WHERE id = ? AND user_id = ?"
        cursor.execute(query, params)
        conn.commit()
        
        return cursor.rowcount > 0


def delete_appointment(appointment_id: int, user_id: int) -> bool:
    """Elimina una cita, verificando que pertenezca al usuario."""
    with sqlite3.connect(str(PERSONAL_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM appointments WHERE id = ? AND user_id = ?", (appointment_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


def get_appointments_count(user_id: int, status: str = None) -> int:
    """Cuenta las citas de un usuario."""
    with sqlite3.connect(str(PERSONAL_DB_PATH)) as conn:
        cursor = conn.cursor()
        query = "SELECT COUNT(*) FROM appointments WHERE user_id = ?"
        params = [user_id]
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        cursor.execute(query, params)
        return cursor.fetchone()[0]


# === TASKS ===

def create_task(
    user_id: int,
    title: str,
    description: str = None,
    due_date: str = None,
    priority: str = "medium",
    category: str = None,
    reminder_minutes: int = 60
) -> int:
    """Crea una nueva tarea para un usuario."""
    with sqlite3.connect(str(PERSONAL_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks 
            (user_id, title, description, due_date, priority, category, reminder_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, title, description, due_date, priority, category, reminder_minutes))
        conn.commit()
        return cursor.lastrowid


def get_task(task_id: int, user_id: int) -> Optional[dict]:
    """Obtiene una tarea por ID, verificando que pertenezca al usuario."""
    with sqlite3.connect(str(PERSONAL_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, title, description, due_date, priority, status,
                   category, reminder_minutes, created_at, updated_at, completed_at
            FROM tasks
            WHERE id = ? AND user_id = ?
        """, (task_id, user_id))
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "user_id": row[1],
                "title": row[2],
                "description": row[3],
                "due_date": row[4],
                "priority": row[5],
                "status": row[6],
                "category": row[7],
                "reminder_minutes": row[8],
                "created_at": row[9],
                "updated_at": row[10],
                "completed_at": row[11]
            }
        return None


def list_tasks(
    user_id: int,
    status: str = None,
    priority: str = None,
    category: str = None
) -> List[dict]:
    """Lista las tareas de un usuario con filtros opcionales."""
    with sqlite3.connect(str(PERSONAL_DB_PATH)) as conn:
        cursor = conn.cursor()
        
        query = """
            SELECT id, user_id, title, description, due_date, priority, status,
                   category, reminder_minutes, created_at, updated_at, completed_at
            FROM tasks
            WHERE user_id = ?
        """
        params = [user_id]
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if priority:
            query += " AND priority = ?"
            params.append(priority)
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        query += " ORDER BY due_date ASC NULLS LAST, priority DESC"
        
        cursor.execute(query, params)
        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                "id": row[0],
                "user_id": row[1],
                "title": row[2],
                "description": row[3],
                "due_date": row[4],
                "priority": row[5],
                "status": row[6],
                "category": row[7],
                "reminder_minutes": row[8],
                "created_at": row[9],
                "updated_at": row[10],
                "completed_at": row[11]
            })
        return tasks


def update_task(
    task_id: int,
    user_id: int,
    title: str = None,
    description: str = None,
    due_date: str = None,
    priority: str = None,
    status: str = None,
    category: str = None,
    reminder_minutes: int = None
) -> bool:
    """Actualiza una tarea, verificando que pertenezca al usuario."""
    with sqlite3.connect(str(PERSONAL_DB_PATH)) as conn:
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if due_date is not None:
            updates.append("due_date = ?")
            params.append(due_date)
        if priority is not None:
            updates.append("priority = ?")
            params.append(priority)
        if status is not None:
            updates.append("status = ?")
            params.append(status)
            # Si se marca como completada, actualizar completed_at
            if status == 'completed':
                updates.append("completed_at = CURRENT_TIMESTAMP")
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if reminder_minutes is not None:
            updates.append("reminder_minutes = ?")
            params.append(reminder_minutes)
        
        if not updates:
            return False
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([task_id, user_id])
        
        query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ? AND user_id = ?"
        cursor.execute(query, params)
        conn.commit()
        
        return cursor.rowcount > 0


def delete_task(task_id: int, user_id: int) -> bool:
    """Elimina una tarea, verificando que pertenezca al usuario."""
    with sqlite3.connect(str(PERSONAL_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


def get_tasks_count(user_id: int, status: str = None) -> int:
    """Cuenta las tareas de un usuario."""
    with sqlite3.connect(str(PERSONAL_DB_PATH)) as conn:
        cursor = conn.cursor()
        query = "SELECT COUNT(*) FROM tasks WHERE user_id = ?"
        params = [user_id]
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        cursor.execute(query, params)
        return cursor.fetchone()[0]


def get_task_categories(user_id: int) -> List[str]:
    """Obtiene todas las categorías únicas de tareas de un usuario."""
    with sqlite3.connect(str(PERSONAL_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT category 
            FROM tasks 
            WHERE user_id = ? AND category IS NOT NULL AND category != ''
            ORDER BY category
        """, (user_id,))
        return [row[0] for row in cursor.fetchall()]
