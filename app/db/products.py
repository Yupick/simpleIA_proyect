"""
Gestión de base de datos para productos comerciales.
Cada usuario tiene su propio catálogo de productos aislado.
"""
from pathlib import Path
import sqlite3
from typing import Optional, List
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent.parent
FEEDBACK_DIR = BASE_DIR / "feedback"
PRODUCTS_DB_PATH = FEEDBACK_DIR / "products.sqlite"

FEEDBACK_DIR.mkdir(exist_ok=True)

def init_products_db():
    """Inicializa la base de datos de productos con aislamiento por usuario."""
    with sqlite3.connect(str(PRODUCTS_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                sku TEXT,
                category TEXT,
                stock INTEGER DEFAULT 0,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Índice para búsquedas rápidas por usuario
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_products_user_id 
            ON products(user_id)
        """)
        
        # Índice para búsquedas por categoría
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_products_category 
            ON products(user_id, category)
        """)
        
        # Índice para búsquedas por SKU
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_products_sku 
            ON products(user_id, sku)
        """)
        
        conn.commit()


def create_product(
    user_id: int,
    name: str,
    price: float,
    description: str = None,
    sku: str = None,
    category: str = None,
    stock: int = 0,
    active: bool = True
) -> int:
    """Crea un nuevo producto para un usuario."""
    with sqlite3.connect(str(PRODUCTS_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO products (user_id, name, description, price, sku, category, stock, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, name, description, price, sku, category, stock, 1 if active else 0))
        conn.commit()
        return cursor.lastrowid


def get_product(product_id: int, user_id: int) -> Optional[dict]:
    """Obtiene un producto por ID, verificando que pertenezca al usuario."""
    with sqlite3.connect(str(PRODUCTS_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, name, description, price, sku, category, stock, active, created_at, updated_at
            FROM products
            WHERE id = ? AND user_id = ?
        """, (product_id, user_id))
        row = cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "user_id": row[1],
                "name": row[2],
                "description": row[3],
                "price": row[4],
                "sku": row[5],
                "category": row[6],
                "stock": row[7],
                "active": bool(row[8]),
                "created_at": row[9],
                "updated_at": row[10]
            }
        return None


def list_products(
    user_id: int,
    category: str = None,
    active_only: bool = True,
    search: str = None
) -> List[dict]:
    """Lista todos los productos de un usuario con filtros opcionales."""
    with sqlite3.connect(str(PRODUCTS_DB_PATH)) as conn:
        cursor = conn.cursor()
        
        query = """
            SELECT id, user_id, name, description, price, sku, category, stock, active, created_at, updated_at
            FROM products
            WHERE user_id = ?
        """
        params = [user_id]
        
        if active_only:
            query += " AND active = 1"
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if search:
            query += " AND (name LIKE ? OR description LIKE ? OR sku LIKE ?)"
            search_pattern = f"%{search}%"
            params.extend([search_pattern, search_pattern, search_pattern])
        
        query += " ORDER BY name ASC"
        
        cursor.execute(query, params)
        products = []
        for row in cursor.fetchall():
            products.append({
                "id": row[0],
                "user_id": row[1],
                "name": row[2],
                "description": row[3],
                "price": row[4],
                "sku": row[5],
                "category": row[6],
                "stock": row[7],
                "active": bool(row[8]),
                "created_at": row[9],
                "updated_at": row[10]
            })
        return products


def update_product(
    product_id: int,
    user_id: int,
    name: str = None,
    description: str = None,
    price: float = None,
    sku: str = None,
    category: str = None,
    stock: int = None,
    active: bool = None
) -> bool:
    """Actualiza un producto, verificando que pertenezca al usuario."""
    with sqlite3.connect(str(PRODUCTS_DB_PATH)) as conn:
        cursor = conn.cursor()
        
        # Construir query dinámicamente con los campos a actualizar
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if price is not None:
            updates.append("price = ?")
            params.append(price)
        if sku is not None:
            updates.append("sku = ?")
            params.append(sku)
        if category is not None:
            updates.append("category = ?")
            params.append(category)
        if stock is not None:
            updates.append("stock = ?")
            params.append(stock)
        if active is not None:
            updates.append("active = ?")
            params.append(1 if active else 0)
        
        if not updates:
            return False
        
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.extend([product_id, user_id])
        
        query = f"UPDATE products SET {', '.join(updates)} WHERE id = ? AND user_id = ?"
        cursor.execute(query, params)
        conn.commit()
        
        return cursor.rowcount > 0


def delete_product(product_id: int, user_id: int) -> bool:
    """Elimina un producto (soft delete), verificando que pertenezca al usuario."""
    with sqlite3.connect(str(PRODUCTS_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE products 
            SET active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        """, (product_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


def hard_delete_product(product_id: int, user_id: int) -> bool:
    """Elimina permanentemente un producto, verificando que pertenezca al usuario."""
    with sqlite3.connect(str(PRODUCTS_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id = ? AND user_id = ?", (product_id, user_id))
        conn.commit()
        return cursor.rowcount > 0


def get_categories(user_id: int) -> List[str]:
    """Obtiene todas las categorías únicas de productos de un usuario."""
    with sqlite3.connect(str(PRODUCTS_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT category 
            FROM products 
            WHERE user_id = ? AND category IS NOT NULL AND category != ''
            ORDER BY category
        """, (user_id,))
        return [row[0] for row in cursor.fetchall()]


def get_product_count(user_id: int, active_only: bool = True) -> int:
    """Cuenta los productos de un usuario."""
    with sqlite3.connect(str(PRODUCTS_DB_PATH)) as conn:
        cursor = conn.cursor()
        query = "SELECT COUNT(*) FROM products WHERE user_id = ?"
        params = [user_id]
        
        if active_only:
            query += " AND active = 1"
        
        cursor.execute(query, params)
        return cursor.fetchone()[0]


def search_products_by_name(user_id: int, name: str) -> List[dict]:
    """Busca productos por nombre (para el asistente LLM)."""
    return list_products(user_id, search=name, active_only=True)
