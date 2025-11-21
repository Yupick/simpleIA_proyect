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
from .db.sqlite import get_feedback_lines, list_users_with_roles, set_admin, get_user, update_user_password
from .security.auth import hash_password
from .models.model_manager import load_model


def cmd_feedback():
    lines = get_feedback_lines()
    print(f"Feedback total: {len(lines)}")
    for i, line in enumerate(lines[:50], 1):  # limitar salida
        print(f"{i:03d}: {line[:200]}")
    if len(lines) > 50:
        print("... (salida truncada) ...")


def cmd_reload():
    name = load_model(force=True)
    if name:
        print(f"Modelo recargado: {name}")
    else:
        print("Error recargando modelo")


def cmd_users_list():
    """Lista todos los usuarios con sus roles."""
    users = list_users_with_roles()
    if not users:
        print("No hay usuarios registrados.")
        return
    
    print(f"\n{'ID':<5} {'Usuario':<20} {'Admin':<10}")
    print("-" * 40)
    for user in users:
        admin_str = "Sí" if user["is_admin"] else "No"
        print(f"{user['id']:<5} {user['username']:<20} {admin_str:<10}")
    print(f"\nTotal: {len(users)} usuario(s)")


def cmd_users_grant_admin(username: str):
    """Otorga permisos de administrador a un usuario."""
    try:
        set_admin(username, True)
        print(f"✓ Permisos de administrador otorgados a '{username}'")
    except ValueError as e:
        print(f"✗ Error: {e}")


def cmd_users_revoke_admin(username: str):
    """Revoca permisos de administrador de un usuario."""
    try:
        set_admin(username, False)
        print(f"✓ Permisos de administrador revocados de '{username}'")
    except ValueError as e:
        print(f"✗ Error: {e}")


def cmd_users_info(username: str):
    """Muestra información detallada de un usuario."""
    user = get_user(username)
    if not user:
        print(f"✗ Usuario '{username}' no encontrado")
        return
    
    print(f"\nInformación del usuario '{username}':")
    print(f"  - Usuario: {user['username']}")
    print(f"  - Administrador: {'Sí' if user.get('is_admin', False) else 'No'}")
    print()


def cmd_users_reset_password(username: str, new_password: str = None):
    """Cambia la contraseña de un usuario."""
    # Verificar que el usuario existe
    user = get_user(username)
    if not user:
        print(f"✗ Usuario '{username}' no encontrado")
        return
    
    # Si no se proporcionó contraseña por argumento, pedirla de forma segura
    if new_password is None:
        print(f"Cambiar contraseña para '{username}'")
        new_password = getpass.getpass("Nueva contraseña: ")
        confirm_password = getpass.getpass("Confirmar contraseña: ")
        
        if new_password != confirm_password:
            print("✗ Error: Las contraseñas no coinciden")
            return
        
        if len(new_password) < 4:
            print("✗ Error: La contraseña debe tener al menos 4 caracteres")
            return
    
    try:
        # Hash de la nueva contraseña
        hashed = hash_password(new_password)
        update_user_password(username, hashed)
        print(f"✓ Contraseña actualizada exitosamente para '{username}'")
    except ValueError as e:
        print(f"✗ Error: {e}")
    except Exception as e:
        print(f"✗ Error inesperado: {e}")


def main():
    if len(sys.argv) < 2:
        print("Uso: python -m app.admin_cli [feedback|reload|users]")
        print("  Ejecuta 'python -m app.admin_cli users' para ver comandos de usuarios")
        return
    
    action = sys.argv[1]
    
    if action == "feedback":
        cmd_feedback()
    elif action == "reload":
        cmd_reload()
    elif action == "users":
        if len(sys.argv) < 3:
            print("Comandos de usuarios:")
            print("  python -m app.admin_cli users list")
            print("  python -m app.admin_cli users grant-admin <username>")
            print("  python -m app.admin_cli users revoke-admin <username>")
            print("  python -m app.admin_cli users info <username>")
            print("  python -m app.admin_cli users reset-password <username> [password]")
            return
        
        subaction = sys.argv[2]
        
        if subaction == "list":
            cmd_users_list()
        elif subaction == "grant-admin":
            if len(sys.argv) < 4:
                print("✗ Error: Debe especificar el nombre de usuario")
                return
            cmd_users_grant_admin(sys.argv[3])
        elif subaction == "revoke-admin":
            if len(sys.argv) < 4:
                print("✗ Error: Debe especificar el nombre de usuario")
                return
            cmd_users_revoke_admin(sys.argv[3])
        elif subaction == "info":
            if len(sys.argv) < 4:
                print("✗ Error: Debe especificar el nombre de usuario")
                return
            cmd_users_info(sys.argv[3])
        elif subaction == "reset-password":
            if len(sys.argv) < 4:
                print("✗ Error: Debe especificar el nombre de usuario")
                return
            # Contraseña opcional como 4to argumento
            password = sys.argv[4] if len(sys.argv) >= 5 else None
            cmd_users_reset_password(sys.argv[3], password)
        else:
            print(f"✗ Subcomando desconocido: {subaction}")
    else:
        print(f"✗ Acción desconocida: {action}")

if __name__ == "__main__":
    main()
