#!/usr/bin/env python3
"""Admin CLI para operaciones básicas del sistema LLM.
Uso:
  python -m app.admin_cli feedback              # Lista feedback almacenado
  python -m app.admin_cli reload                # Recarga modelo según config
  python -m app.admin_cli users list            # Lista todos los usuarios con roles
  python -m app.admin_cli users grant-admin <username>  # Otorga permisos de admin
  python -m app.admin_cli users revoke-admin <username> # Revoca permisos de admin
  python -m app.admin_cli users info <username>         # Muestra información del usuario
  python -m app.admin_cli users reset-password <username> <new_password>  # Cambia contraseña
"""

import sys
import getpass
import logging
from .db.sqlite import (
    get_feedback_lines,
    list_users_with_roles,
    set_admin,
    get_user,
    update_user_password,
)
from .security.auth import hash_password
from .models.model_manager import load_model

logger = logging.getLogger(__name__)


def cmd_feedback():
    lines = get_feedback_lines()
    logger.info(f"Feedback total: {len(lines)}")
    for i, line in enumerate(lines[:50], 1):  # limitar salida
        logger.info(f"{i:03d}: {line[:200]}")
    if len(lines) > 50:
        logger.info("... (salida truncada) ...")


def cmd_reload():
    name = load_model(force=True)
    if name:
        logger.info(f"Modelo recargado: {name}")
    else:
        logger.error("Error recargando modelo")


def cmd_users_list():
    """Lista todos los usuarios con sus roles."""
    users = list_users_with_roles()
    if not users:
        logger.info("No hay usuarios registrados.")
        return

    logger.info(f"\n{'ID':<5} {'Usuario':<20} {'Admin':<10}")
    logger.info("-" * 40)
    for user in users:
        admin_str = "Sí" if user["is_admin"] else "No"
        logger.info(f"{user['id']:<5} {user['username']:<20} {admin_str:<10}")
    logger.info(f"\nTotal: {len(users)} usuario(s)")


def cmd_users_grant_admin(username: str):
    """Otorga permisos de administrador a un usuario."""
    try:
        set_admin(username, True)
        logger.info(f"Permisos de administrador otorgados a '{username}'")
    except ValueError as e:
        logger.error(f"Error: {e}")


def cmd_users_revoke_admin(username: str):
    """Revoca permisos de administrador de un usuario."""
    try:
        set_admin(username, False)
        logger.info(f"Permisos de administrador revocados de '{username}'")
    except ValueError as e:
        logger.error(f"Error: {e}")


def cmd_users_info(username: str):
    """Muestra información detallada de un usuario."""
    user = get_user(username)
    if not user:
        logger.error(f"Usuario '{username}' no encontrado")
        return

    logger.info(f"\nInformación del usuario '{username}':")
    logger.info(f"  - Usuario: {user['username']}")
    logger.info(f"  - Administrador: {'Sí' if user.get('is_admin', False) else 'No'}")
    logger.info("")


def cmd_users_reset_password(username: str, new_password: str = None):
    """Cambia la contraseña de un usuario."""
    # Verificar que el usuario existe
    user = get_user(username)
    if not user:
        logger.error(f"Usuario '{username}' no encontrado")
        return

    # Si no se proporcionó contraseña por argumento, pedirla de forma segura
    if new_password is None:
        logger.info(f"Cambiar contraseña para '{username}'")
        new_password = getpass.getpass("Nueva contraseña: ")
        confirm_password = getpass.getpass("Confirmar contraseña: ")

        if new_password != confirm_password:
            logger.error("Las contraseñas no coinciden")
            return

        if len(new_password) < 4:
            logger.error("La contraseña debe tener al menos 4 caracteres")
            return

    try:
        # Hash de la nueva contraseña
        hashed = hash_password(new_password)
        update_user_password(username, hashed)
        logger.info(f"Contraseña actualizada exitosamente para '{username}'")
    except ValueError as e:
        logger.error(f"Error: {e}")
    except Exception as e:
        logger.exception(f"Error inesperado: {e}")


def main():
    if len(sys.argv) < 2:
        logger.info("Uso: python -m app.admin_cli [feedback|reload|users]")
        logger.info(
            "  Ejecuta 'python -m app.admin_cli users' para ver comandos de usuarios"
        )
        return

    action = sys.argv[1]

    if action == "feedback":
        cmd_feedback()
    elif action == "reload":
        cmd_reload()
    elif action == "users":
        if len(sys.argv) < 3:
            logger.info("Comandos de usuarios:")
            logger.info("  python -m app.admin_cli users list")
            logger.info("  python -m app.admin_cli users grant-admin <username>")
            logger.info("  python -m app.admin_cli users revoke-admin <username>")
            logger.info("  python -m app.admin_cli users info <username>")
            logger.info(
                "  python -m app.admin_cli users reset-password <username> [password]"
            )
            return

        subaction = sys.argv[2]

        if subaction == "list":
            cmd_users_list()
        elif subaction == "grant-admin":
            if len(sys.argv) < 4:
                logger.error("Debe especificar el nombre de usuario")
                return
            cmd_users_grant_admin(sys.argv[3])
        elif subaction == "revoke-admin":
            if len(sys.argv) < 4:
                logger.error("Debe especificar el nombre de usuario")
                return
            cmd_users_revoke_admin(sys.argv[3])
        elif subaction == "info":
            if len(sys.argv) < 4:
                logger.error("Debe especificar el nombre de usuario")
                return
            cmd_users_info(sys.argv[3])
        elif subaction == "reset-password":
            if len(sys.argv) < 4:
                logger.error("Debe especificar el nombre de usuario")
                return
            # Contraseña opcional como 4to argumento
            password = sys.argv[4] if len(sys.argv) >= 5 else None
            cmd_users_reset_password(sys.argv[3], password)
        else:
            logger.error(f"Subcomando desconocido: {subaction}")
    else:
        logger.error(f"Acción desconocida: {action}")


if __name__ == "__main__":
    main()
