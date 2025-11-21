"""
config_db.py
------------
Gestión de configuración personalizable del sistema almacenada en SQLite.
"""

from pathlib import Path
import sqlite3
from typing import Optional, Dict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FEEDBACK_DIR = BASE_DIR / "feedback"
CONFIG_DB_PATH = FEEDBACK_DIR / "config.sqlite"

FEEDBACK_DIR.mkdir(exist_ok=True)


def init_config_db():
    """Inicializa la tabla de configuración con valores por defecto."""
    with sqlite3.connect(str(CONFIG_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS app_config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.commit()
        
        # Insertar valores por defecto si no existen
        defaults = {
            "app_name": "SimpleIA",
            "llm_name": "Asistente",
            "llm_personality": "Soy un asistente virtual inteligente llamado {llm_name}. Estoy aquí para ayudarte con tus preguntas de manera amable y precisa.",
            "primary_color": "#4A90E2",
            "logo_url": "",
        }
        
        for key, value in defaults.items():
            cursor.execute(
                "INSERT OR IGNORE INTO app_config (key, value) VALUES (?, ?)",
                (key, value)
            )
        conn.commit()


def get_config(key: str) -> Optional[str]:
    """Obtiene un valor de configuración."""
    with sqlite3.connect(str(CONFIG_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM app_config WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else None


def set_config(key: str, value: str):
    """Actualiza o inserta un valor de configuración."""
    with sqlite3.connect(str(CONFIG_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO app_config (key, value) VALUES (?, ?)",
            (key, value)
        )
        conn.commit()


def get_all_config() -> Dict[str, str]:
    """Obtiene toda la configuración como diccionario."""
    with sqlite3.connect(str(CONFIG_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM app_config")
        return {row[0]: row[1] for row in cursor.fetchall()}


def delete_config(key: str):
    """Elimina una clave de configuración."""
    with sqlite3.connect(str(CONFIG_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM app_config WHERE key = ?", (key,))
        conn.commit()


# Inicializar la base de datos al importar el módulo
init_config_db()
