#!/usr/bin/env python3
"""
Script para dar permisos de administrador al usuario 'admin'.
Útil cuando el usuario admin no tiene permisos correctos.
"""

import sqlite3
import logging
from pathlib import Path

USER_DB_PATH = Path(__file__).parent / "feedback" / "users.sqlite"

logger = logging.getLogger(__name__)


def fix_admin_user():
    """Actualiza el usuario 'admin' para que tenga permisos de superadmin."""
    if not USER_DB_PATH.exists():
        logger.error("No se encontró la base de datos en %s", USER_DB_PATH)
        return False

    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()

        # Verificar si existe el usuario admin
        cursor.execute(
            "SELECT username, is_admin, role FROM users WHERE username = 'admin'"
        )
        user = cursor.fetchone()

        if not user:
            logger.error(
                "Usuario 'admin' no encontrado. Crea el usuario primero usando el endpoint de registro."
            )
            return False

        username, is_admin, role = user
        logger.info(
            "Estado actual: username=%s, is_admin=%s, role=%s", username, is_admin, role
        )

        # Actualizar permisos
        cursor.execute(
            """
            UPDATE users
            SET is_admin = 1, role = 'superadmin'
            WHERE username = 'admin'
        """
        )
        conn.commit()

        # Verificar actualización
        cursor.execute(
            "SELECT username, is_admin, role FROM users WHERE username = 'admin'"
        )
        updated_user = cursor.fetchone()
        username, is_admin, role = updated_user

        logger.info(
            "Usuario actualizado: username=%s, is_admin=%s, role=%s",
            username,
            is_admin,
            role,
        )
        logger.info(
            "Para mayor seguridad, restablece la contraseña del usuario admin mediante el endpoint de cambio de contraseña o un proceso seguro."
        )
        return True


if __name__ == "__main__":
    logger.info("Actualizando permisos de usuario admin...")
    fix_admin_user()
