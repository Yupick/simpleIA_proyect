"""
Gestión de historial de conversaciones por usuario.
"""
from pathlib import Path
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FEEDBACK_DIR = BASE_DIR / "feedback"
CONVERSATIONS_DB_PATH = FEEDBACK_DIR / "conversations.sqlite"

FEEDBACK_DIR.mkdir(exist_ok=True)


def init_conversations_db():
    """Inicializa la base de datos de conversaciones."""
    with sqlite3.connect(str(CONVERSATIONS_DB_PATH)) as conn:
        cursor = conn.cursor()
        
        # Tabla de conversaciones
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                assistant_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Tabla de mensajes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        
        # Tabla de analytics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                event_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Índices
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_user_id 
            ON conversations(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_id 
            ON messages(conversation_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analytics_user_id 
            ON user_analytics(user_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_analytics_event_type 
            ON user_analytics(user_id, event_type)
        """)
        
        conn.commit()


# === CONVERSATIONS ===

def create_conversation(user_id: int, assistant_type: str) -> int:
    """Crea una nueva conversación."""
    with sqlite3.connect(str(CONVERSATIONS_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversations (user_id, assistant_type)
            VALUES (?, ?)
        """, (user_id, assistant_type))
        conn.commit()
        return cursor.lastrowid


def get_conversation(conversation_id: int, user_id: int) -> Optional[Dict]:
    """Obtiene una conversación verificando que pertenezca al usuario."""
    with sqlite3.connect(str(CONVERSATIONS_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, assistant_type, created_at, updated_at
            FROM conversations
            WHERE id = ? AND user_id = ?
        """, (conversation_id, user_id))
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "user_id": row[1],
                "assistant_type": row[2],
                "created_at": row[3],
                "updated_at": row[4]
            }
        return None


def list_conversations(user_id: int, assistant_type: str = None, limit: int = 50) -> List[Dict]:
    """Lista las conversaciones de un usuario."""
    with sqlite3.connect(str(CONVERSATIONS_DB_PATH)) as conn:
        cursor = conn.cursor()
        
        query = """
            SELECT id, user_id, assistant_type, created_at, updated_at
            FROM conversations
            WHERE user_id = ?
        """
        params = [user_id]
        
        if assistant_type:
            query += " AND assistant_type = ?"
            params.append(assistant_type)
        
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        conversations = []
        for row in cursor.fetchall():
            conversations.append({
                "id": row[0],
                "user_id": row[1],
                "assistant_type": row[2],
                "created_at": row[3],
                "updated_at": row[4]
            })
        return conversations


def delete_conversation(conversation_id: int, user_id: int) -> bool:
    """Elimina una conversación y sus mensajes."""
    with sqlite3.connect(str(CONVERSATIONS_DB_PATH)) as conn:
        cursor = conn.cursor()
        
        # Verificar que pertenece al usuario
        cursor.execute("SELECT id FROM conversations WHERE id = ? AND user_id = ?", 
                      (conversation_id, user_id))
        if not cursor.fetchone():
            return False
        
        # Eliminar mensajes
        cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        
        # Eliminar conversación
        cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        
        conn.commit()
        return True


# === MESSAGES ===

def add_message(conversation_id: int, role: str, content: str) -> int:
    """Agrega un mensaje a una conversación."""
    with sqlite3.connect(str(CONVERSATIONS_DB_PATH)) as conn:
        cursor = conn.cursor()
        
        # Agregar mensaje
        cursor.execute("""
            INSERT INTO messages (conversation_id, role, content)
            VALUES (?, ?, ?)
        """, (conversation_id, role, content))
        
        # Actualizar timestamp de conversación
        cursor.execute("""
            UPDATE conversations 
            SET updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (conversation_id,))
        
        conn.commit()
        return cursor.lastrowid


def get_conversation_messages(conversation_id: int, limit: int = 100) -> List[Dict]:
    """Obtiene los mensajes de una conversación."""
    with sqlite3.connect(str(CONVERSATIONS_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, conversation_id, role, content, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            LIMIT ?
        """, (conversation_id, limit))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                "id": row[0],
                "conversation_id": row[1],
                "role": row[2],
                "content": row[3],
                "created_at": row[4]
            })
        return messages


# === ANALYTICS ===

def track_event(user_id: int, event_type: str, event_data: str = None):
    """Registra un evento de analytics."""
    with sqlite3.connect(str(CONVERSATIONS_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_analytics (user_id, event_type, event_data)
            VALUES (?, ?, ?)
        """, (user_id, event_type, event_data))
        conn.commit()


def get_user_stats(user_id: int) -> Dict:
    """Obtiene estadísticas del usuario."""
    with sqlite3.connect(str(CONVERSATIONS_DB_PATH)) as conn:
        cursor = conn.cursor()
        
        # Total de conversaciones
        cursor.execute("""
            SELECT COUNT(*) FROM conversations WHERE user_id = ?
        """, (user_id,))
        total_conversations = cursor.fetchone()[0]
        
        # Total de mensajes
        cursor.execute("""
            SELECT COUNT(*) FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            WHERE c.user_id = ?
        """, (user_id,))
        total_messages = cursor.fetchone()[0]
        
        # Conversaciones por tipo
        cursor.execute("""
            SELECT assistant_type, COUNT(*) as count
            FROM conversations
            WHERE user_id = ?
            GROUP BY assistant_type
        """, (user_id,))
        conversations_by_type = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Eventos recientes
        cursor.execute("""
            SELECT event_type, COUNT(*) as count
            FROM user_analytics
            WHERE user_id = ?
            GROUP BY event_type
            ORDER BY count DESC
            LIMIT 10
        """, (user_id,))
        events = {row[0]: row[1] for row in cursor.fetchall()}
        
        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "conversations_by_type": conversations_by_type,
            "events": events
        }


def get_recent_activity(user_id: int, days: int = 7) -> List[Dict]:
    """Obtiene la actividad reciente del usuario."""
    with sqlite3.connect(str(CONVERSATIONS_DB_PATH)) as conn:
        cursor = conn.cursor()
        
        # Fecha límite
        from datetime import timedelta
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            SELECT event_type, event_data, created_at
            FROM user_analytics
            WHERE user_id = ? AND created_at >= ?
            ORDER BY created_at DESC
            LIMIT 50
        """, (user_id, cutoff_date))
        
        activity = []
        for row in cursor.fetchall():
            activity.append({
                "event_type": row[0],
                "event_data": row[1],
                "created_at": row[2]
            })
        return activity
