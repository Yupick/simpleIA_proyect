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
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                hashed_password TEXT,
                is_admin INTEGER DEFAULT 0
            )
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

def create_user(username: str, hashed_password: str, is_admin: bool = False):
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, hashed_password, is_admin) VALUES (?, ?, ?)", 
                      (username, hashed_password, 1 if is_admin else 0))
        conn.commit()

def get_user(username: str) -> Optional[dict]:
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, hashed_password, is_admin FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            return {"username": row[0], "hashed_password": row[1], "is_admin": bool(row[2])}
        return None

def is_first_user() -> bool:
    """Verifica si la tabla users está vacía (primer usuario)."""
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        return count == 0

def set_admin(username: str, is_admin: bool):
    """Establece el estado de administrador de un usuario."""
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_admin = ? WHERE username = ?", 
                      (1 if is_admin else 0, username))
        conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Usuario '{username}' no encontrado")

def list_users_with_roles() -> list[dict]:
    """Lista todos los usuarios con sus roles."""
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, is_admin FROM users")
        users = []
        for row in cursor.fetchall():
            users.append({
                "id": row[0],
                "username": row[1],
                "is_admin": bool(row[2])
            })
        return users

def update_user_password(username: str, new_hashed_password: str):
    """Actualiza la contraseña de un usuario."""
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET hashed_password = ? WHERE username = ?", 
                      (new_hashed_password, username))
        conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Usuario '{username}' no encontrado")
