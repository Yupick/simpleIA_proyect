#!/usr/bin/env python3
"""
Script para dar permisos de administrador al usuario 'admin'.
Útil cuando el usuario admin no tiene permisos correctos.
"""
import sqlite3
from pathlib import Path

USER_DB_PATH = Path(__file__).parent / "feedback" / "users.sqlite"

def fix_admin_user():
    """Actualiza el usuario 'admin' para que tenga permisos de superadmin."""
    if not USER_DB_PATH.exists():
        print(f"❌ Error: No se encontró la base de datos en {USER_DB_PATH}")
        return False
    
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        
        # Verificar si existe el usuario admin
        cursor.execute("SELECT username, is_admin, role FROM users WHERE username = 'admin'")
        user = cursor.fetchone()
        
        if not user:
            print("❌ Usuario 'admin' no encontrado")
            print("   Crea el usuario primero con: curl -X POST http://localhost:8000/auth/register ...")
            return False
        
        username, is_admin, role = user
        print(f"📋 Estado actual: username={username}, is_admin={is_admin}, role={role}")
        
        # Actualizar permisos
        cursor.execute("""
            UPDATE users 
            SET is_admin = 1, role = 'superadmin'
            WHERE username = 'admin'
        """)
        conn.commit()
        
        # Verificar actualización
        cursor.execute("SELECT username, is_admin, role FROM users WHERE username = 'admin'")
        updated_user = cursor.fetchone()
        username, is_admin, role = updated_user
        
        print(f"✅ Usuario actualizado: username={username}, is_admin={is_admin}, role={role}")
        print("\n💡 Ahora puedes hacer login con:")
        print("   username: admin")
        print("   password: admin123")
        return True

if __name__ == "__main__":
    print("🔧 Actualizando permisos de usuario admin...\n")
    fix_admin_user()
