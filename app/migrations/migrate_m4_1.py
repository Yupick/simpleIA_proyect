#!/usr/bin/env python3
"""
Migración M4.1 - Actualizar base de datos con columna 'role'
Ejecutar una sola vez para actualizar la estructura de la DB existente.
"""

import sqlite3
import sys
from pathlib import Path

# Agregar el directorio raíz al path para importar módulos
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

FEEDBACK_DIR = BASE_DIR / "feedback"
USER_DB_PATH = FEEDBACK_DIR / "users.sqlite"

# Crear directorio si no existe
FEEDBACK_DIR.mkdir(exist_ok=True)

def migrate_users_db():
    """Migra la base de datos de usuarios para agregar columna 'role'."""
    
    print("🔄 Iniciando migración de base de datos...")
    
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        
        # Verificar si la columna 'role' ya existe
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'role' in columns:
            print("✅ La columna 'role' ya existe. No se requiere migración.")
        else:
            print("📝 Agregando columna 'role' a la tabla users...")
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
            conn.commit()
            print("✅ Columna 'role' agregada exitosamente.")
        
        if 'created_at' not in columns:
            print("📝 Agregando columna 'created_at' a la tabla users...")
            cursor.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP")
            # Actualizar registros existentes con timestamp actual
            cursor.execute("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
            conn.commit()
            print("✅ Columna 'created_at' agregada exitosamente.")
        
        # Actualizar roles basados en is_admin
        print("📝 Actualizando roles basados en is_admin...")
        cursor.execute("""
            UPDATE users 
            SET role = 'superadmin'
            WHERE is_admin = 1
        """)
        affected = cursor.rowcount
        conn.commit()
        print(f"✅ {affected} administradores actualizados a role='superadmin'.")
        
        # Mostrar usuarios y sus roles
        print("\n📊 Usuarios en el sistema:")
        cursor.execute("SELECT id, username, is_admin, role FROM users")
        for row in cursor.fetchall():
            print(f"  - ID: {row[0]}, Usuario: {row[1]}, is_admin: {row[2]}, role: {row[3]}")
    
    print("\n✅ Migración completada exitosamente!")

if __name__ == "__main__":
    migrate_users_db()
