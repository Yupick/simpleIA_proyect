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
                hashed_password TEXT
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

def create_user(username: str, hashed_password: str):
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, hashed_password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()

def get_user(username: str) -> Optional[dict]:
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, hashed_password FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if row:
            return {"username": row[0], "hashed_password": row[1]}
        return None
