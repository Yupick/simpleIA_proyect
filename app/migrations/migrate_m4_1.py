#!/usr/bin/env python3
"""
Migración M4.1 - Actualizar base de datos con columna 'role'
Ejecutar una sola vez para actualizar la estructura de la DB existente.
"""

import sqlite3
import sys
import logging
from pathlib import Path

# Agregar el directorio raíz al path para importar módulos
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

FEEDBACK_DIR = BASE_DIR / "feedback"
USER_DB_PATH = FEEDBACK_DIR / "users.sqlite"

logger = logging.getLogger(__name__)

# Crear directorio si no existe
FEEDBACK_DIR.mkdir(exist_ok=True)


def migrate_users_db():
    """Migra la base de datos de usuarios para agregar columna 'role'."""

    logger.info("🔄 Iniciando migración de base de datos...")

    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()

        # Verificar si la columna 'role' ya existe
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]

        if "role" in columns:
            logger.info("✅ La columna 'role' ya existe. No se requiere migración.")
        else:
            logger.info("📝 Agregando columna 'role' a la tabla users...")
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
            conn.commit()
            logger.info("✅ Columna 'role' agregada exitosamente.")

        if "created_at" not in columns:
            logger.info("📝 Agregando columna 'created_at' a la tabla users...")
            cursor.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP")
            # Actualizar registros existentes con timestamp actual
            cursor.execute(
                "UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"
            )
            conn.commit()
            logger.info("✅ Columna 'created_at' agregada exitosamente.")

        # Actualizar roles basados en is_admin
        logger.info("📝 Actualizando roles basados en is_admin...")
        cursor.execute(
            """
            UPDATE users
            SET role = 'superadmin'
            WHERE is_admin = 1
        """
        )
        affected = cursor.rowcount
        conn.commit()
        logger.info("✅ %s administradores actualizados a role='superadmin'.", affected)

        # Mostrar usuarios y sus roles
        logger.info("\n📊 Usuarios en el sistema:")
        cursor.execute("SELECT id, username, is_admin, role FROM users")
        for row in cursor.fetchall():
            logger.info(
                "  - ID: %s, Usuario: %s, is_admin: %s, role: %s",
                row[0],
                row[1],
                row[2],
                row[3],
            )

    logger.info("\n✅ Migración completada exitosamente!")


if __name__ == "__main__":
    migrate_users_db()
