from pathlib import Path
import sqlite3
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FEEDBACK_DIR = BASE_DIR / "feedback"
FEEDBACK_DB_PATH = FEEDBACK_DIR / "feedback.sqlite"
USER_DB_PATH = FEEDBACK_DIR / "users.sqlite"

FEEDBACK_DIR.mkdir(exist_ok=True)

def init_feedback_db():
    with sqlite3.connect(str(FEEDBACK_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def init_user_db():
    """Inicializa la base de datos de usuarios con soporte para roles."""
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                hashed_password TEXT,
                is_admin INTEGER DEFAULT 0,
                role TEXT DEFAULT 'user',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Migrar datos existentes: actualizar role basado en is_admin
        cursor.execute("""
            UPDATE users 
            SET role = CASE 
                WHEN is_admin = 1 THEN 'superadmin'
                ELSE 'user'
            END
            WHERE role IS NULL OR role = ''
        """)
        
        conn.commit()

def store_feedback(text: str):
    with sqlite3.connect(str(FEEDBACK_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO feedback (text) VALUES (?)", (text,))
        conn.commit()

def get_feedback_lines():
    with sqlite3.connect(str(FEEDBACK_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT text FROM feedback")
        return [r[0] for r in cursor.fetchall()]

def create_user(username: str, hashed_password: str, is_admin: bool = False, role: str = None):
    """Crea un nuevo usuario con soporte para roles."""
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        # Determinar role: usar parámetro role o inferir de is_admin
        user_role = role if role else ('superadmin' if is_admin else 'user')
        cursor.execute(
            "INSERT INTO users (username, hashed_password, is_admin, role) VALUES (?, ?, ?, ?)", 
            (username, hashed_password, 1 if is_admin else 0, user_role)
        )
        conn.commit()

def get_user(username: str) -> Optional[dict]:
    """Obtiene un usuario por username incluyendo su role."""
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, hashed_password, is_admin, role FROM users WHERE username = ?", 
            (username,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "username": row[1], 
                "hashed_password": row[2], 
                "is_admin": bool(row[3]),
                "role": row[4] or ('superadmin' if row[3] else 'user')  # Fallback por migración
            }
        return None

def is_first_user() -> bool:
    """Verifica si la tabla users está vacía (primer usuario)."""
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        return count == 0

def set_admin(username: str, is_admin: bool):
    """Establece el estado de administrador de un usuario (actualiza is_admin y role)."""
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        role = 'superadmin' if is_admin else 'user'
        cursor.execute(
            "UPDATE users SET is_admin = ?, role = ? WHERE username = ?", 
            (1 if is_admin else 0, role, username)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Usuario '{username}' no encontrado")

def set_user_role(username: str, role: str):
    """Establece el role de un usuario. Valores válidos: 'user', 'superadmin'."""
    if role not in ['user', 'superadmin']:
        raise ValueError(f"Role inválido: {role}. Debe ser 'user' o 'superadmin'")
    
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        is_admin = 1 if role == 'superadmin' else 0
        cursor.execute(
            "UPDATE users SET role = ?, is_admin = ? WHERE username = ?",
            (role, is_admin, username)
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Usuario '{username}' no encontrado")

def list_users_with_roles() -> list[dict]:
    """Lista todos los usuarios con sus roles."""
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, is_admin, role, created_at FROM users")
        users = []
        for row in cursor.fetchall():
            users.append({
                "id": row[0],
                "username": row[1],
                "is_admin": bool(row[2]),
                "role": row[3] or ('superadmin' if row[2] else 'user'),
                "created_at": row[4]
            })
        return users

def get_user_by_id(user_id: int) -> Optional[dict]:
    """Obtiene un usuario por ID."""
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, hashed_password, is_admin, role FROM users WHERE id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "username": row[1],
                "hashed_password": row[2],
                "is_admin": bool(row[3]),
                "role": row[4] or ('superadmin' if row[3] else 'user')
            }
        return None

def update_user_password(username: str, new_hashed_password: str):
    """Actualiza la contraseña de un usuario."""
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET hashed_password = ? WHERE username = ?", 
                      (new_hashed_password, username))
        conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Usuario '{username}' no encontrado")
