"""
Router para el panel de administración.
"""

from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, Dict
from ...security.auth import get_current_user, get_current_admin_user, hash_password
from ...db.sqlite import list_users_with_roles, set_admin, get_user
from ...db.config_db import get_config, set_config, get_all_config
import sqlite3
from pathlib import Path

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")

# Modelos Pydantic
class RoleUpdate(BaseModel):
    is_admin: bool

class UserDelete(BaseModel):
    confirm: bool = True

class ConfigUpdate(BaseModel):
    key: str
    value: str

class ProviderSwitch(BaseModel):
    provider: str
    model: str
    api_key: Optional[str] = None
    # Campos Claude
    api_version: Optional[str] = None
    max_tokens: Optional[int] = None
    # Campos OpenAI
    organization_id: Optional[str] = None
    base_url: Optional[str] = None

@router.get("", response_class=HTMLResponse)
async def admin_dashboard(request: Request, current_user=Depends(get_current_admin_user)):
    """
    Panel de administración con métricas visuales.
    Requiere permisos de administrador.
    """
    return templates.TemplateResponse("admin.html", {"request": request, "user": current_user})


# ===== ENDPOINTS GESTIÓN DE USUARIOS =====

@router.get("/users")
async def list_users(
    page: int = 1,
    limit: int = 20,
    current_user=Depends(get_current_admin_user)
):
    """
    Lista todos los usuarios con paginación.
    Requiere permisos de administrador.
    """
    users = list_users_with_roles()
    total = len(users)
    start = (page - 1) * limit
    end = start + limit
    
    return {
        "users": users[start:end],
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }


@router.post("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role_update: RoleUpdate,
    current_user=Depends(get_current_admin_user)
):
    """
    Actualiza el rol de administrador de un usuario.
    Requiere permisos de administrador.
    """
    # Obtener usuario por ID
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    USER_DB_PATH = BASE_DIR / "feedback" / "users.sqlite"
    
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        username = row[0]
    
    # No permitir auto-revocación del último admin
    if not role_update.is_admin and current_user["username"] == username:
        users = list_users_with_roles()
        admin_count = sum(1 for u in users if u["is_admin"])
        if admin_count <= 1:
            raise HTTPException(
                status_code=400, 
                detail="No puedes revocar tus propios permisos siendo el único administrador"
            )
    
    try:
        set_admin(username, role_update.is_admin)
        return {
            "message": f"Rol actualizado para {username}",
            "username": username,
            "is_admin": role_update.is_admin
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user=Depends(get_current_admin_user)
):
    """
    Elimina un usuario del sistema.
    Requiere permisos de administrador.
    """
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    USER_DB_PATH = BASE_DIR / "feedback" / "users.sqlite"
    
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        
        # Verificar que el usuario existe
        cursor.execute("SELECT username, is_admin FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        username, is_admin = row[0], bool(row[1])
        
        # No permitir auto-eliminación
        if current_user["username"] == username:
            raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta")
        
        # No permitir eliminar al último admin
        if is_admin:
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
            admin_count = cursor.fetchone()[0]
            if admin_count <= 1:
                raise HTTPException(
                    status_code=400,
                    detail="No se puede eliminar al único administrador del sistema"
                )
        
        # Eliminar usuario
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    
    return {"message": f"Usuario '{username}' eliminado exitosamente"}


# ===== ENDPOINTS CONFIGURACIÓN =====

@router.get("/config")
async def get_configuration(current_user=Depends(get_current_admin_user)) -> Dict[str, str]:
    """
    Obtiene toda la configuración del sistema.
    Requiere permisos de administrador.
    """
    return get_all_config()


@router.post("/config")
async def update_configuration(
    config: ConfigUpdate,
    current_user=Depends(get_current_admin_user)
):
    """
    Actualiza una clave de configuración.
    Requiere permisos de administrador.
    """
    allowed_keys = [
        "app_name",
        "llm_name",
        "llm_personality",
        "primary_color",
        "logo_url"
    ]
    
    if config.key not in allowed_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Clave no permitida. Permitidas: {', '.join(allowed_keys)}"
        )
    
    set_config(config.key, config.value)
    
    return {
        "message": f"Configuración '{config.key}' actualizada",
        "key": config.key,
        "value": config.value
    }


@router.post("/config/logo")
async def upload_logo(
    file: UploadFile = File(...),
    current_user=Depends(get_current_admin_user)
):
    """
    Sube un logo personalizado.
    Requiere permisos de administrador.
    """
    # Validar tipo de archivo
    allowed_types = ["image/png", "image/jpeg", "image/jpg", "image/gif", "image/svg+xml"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Tipo de archivo no permitido. Use PNG, JPG, GIF o SVG."
        )
    
    # Guardar archivo
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    static_dir = BASE_DIR / "static"
    static_dir.mkdir(exist_ok=True)
    
    # Generar nombre único
    import time
    ext = file.filename.split(".")[-1]
    filename = f"logo_{int(time.time())}.{ext}"
    filepath = static_dir / filename
    
    # Guardar archivo
    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Actualizar configuración
    logo_url = f"/static/{filename}"
    set_config("logo_url", logo_url)
    
    return {
        "message": "Logo subido exitosamente",
        "logo_url": logo_url
    }


# ===== ENDPOINTS FEEDBACK =====

@router.get("/feedback")
async def list_feedback(
    page: int = 1,
    limit: int = 50,
    search: Optional[str] = None,
    current_user=Depends(get_current_admin_user)
):
    """
    Lista todo el feedback con filtros y paginación.
    Requiere permisos de administrador.
    """
    from ...db.sqlite import FEEDBACK_DB_PATH
    
    with sqlite3.connect(str(FEEDBACK_DB_PATH)) as conn:
        cursor = conn.cursor()
        
        # Construir query con filtros
        query = "SELECT id, text, timestamp FROM feedback"
        params = []
        
        if search:
            query += " WHERE text LIKE ?"
            params.append(f"%{search}%")
        
        query += " ORDER BY timestamp DESC"
        
        # Contar total
        count_query = query.replace("SELECT id, text, timestamp", "SELECT COUNT(*)")
        cursor.execute(count_query, params)
        total = cursor.fetchone()[0]
        
        # Aplicar paginación
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, (page - 1) * limit])
        
        cursor.execute(query, params)
        feedbacks = []
        for row in cursor.fetchall():
            feedbacks.append({
                "id": row[0],
                "text": row[1],
                "timestamp": row[2]
            })
    
    return {
        "feedbacks": feedbacks,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit
    }


@router.delete("/feedback/{feedback_id}")
async def delete_feedback(
    feedback_id: int,
    current_user=Depends(get_current_admin_user)
):
    """
    Elimina un feedback.
    Requiere permisos de administrador.
    """
    from ...db.sqlite import FEEDBACK_DB_PATH
    
    with sqlite3.connect(str(FEEDBACK_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM feedback WHERE id = ?", (feedback_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Feedback no encontrado")
    
    return {"message": "Feedback eliminado exitosamente"}


# ===== ENDPOINTS PROVIDERS =====

@router.get("/providers/current")
async def get_current_provider(current_user=Depends(get_current_admin_user)):
    """
    Obtiene el provider actual configurado y todas las API keys guardadas.
    Requiere permisos de administrador.
    """
    from ...core.settings import settings
    import json
    
    # Intentar leer desde config.json primero
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    config_path = BASE_DIR / "config" / "config.json"
    
    provider = "huggingface"  # Default
    model = settings.DEFAULT_MODEL
    saved_keys = {}
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                provider = config.get("provider", provider)
                model = config.get("model_name", config.get("selected_model", model))
                
                # Extraer todas las API keys y configuraciones guardadas
                saved_keys = {
                    "openai_api_key": config.get("openai_api_key", ""),
                    "anthropic_api_key": config.get("anthropic_api_key", ""),
                    "api_version": config.get("anthropic_api_version", ""),
                    "max_tokens": config.get("max_tokens", 4096),
                    "organization_id": config.get("openai_organization_id", ""),
                    "base_url": config.get("openai_base_url", "")
                }
        except Exception as e:
            print(f"Error leyendo config.json: {e}")
    
    # Normalizar provider a formato interno
    provider_mapping = {
        "huggingface": "hf",
        "hf": "hf",
        "claude": "claude",
        "openai": "openai"
    }
    
    provider = provider_mapping.get(provider, provider)
    
    # Mapear para display
    display_mapping = {
        "hf": "huggingface",
        "claude": "claude",
        "openai": "openai"
    }
    
    return {
        "provider": display_mapping.get(provider, provider),
        "model": model,
        "available_providers": ["huggingface", "claude", "openai"],
        "saved_keys": saved_keys
    }


@router.get("/providers/models")
async def get_available_models(
    provider: Optional[str] = None,
    current_user=Depends(get_current_admin_user)
):
    """
    Obtiene lista de modelos disponibles por provider.
    Si no se especifica provider, retorna todos.
    Requiere permisos de administrador.
    """
    # Modelos disponibles por provider
    all_models = {
        "huggingface": {
            "spanish": [
                {"id": "DeepESP/gpt2-spanish", "name": "GPT-2 Spanish (DeepESP) ⭐", "size": "500MB"},
                {"id": "PlanTL-GOB-ES/gpt2-base-bne", "name": "GPT-2 BNE (Gobierno ES) ⭐", "size": "500MB"},
                {"id": "datificate/gpt2-small-spanish", "name": "GPT-2 Small Spanish", "size": "500MB"},
                {"id": "flax-community/gpt-2-spanish", "name": "GPT-2 Spanish (Flax)", "size": "500MB"},
            ],
            "english": [
                {"id": "gpt2", "name": "GPT-2 Base", "size": "500MB"},
                {"id": "gpt2-medium", "name": "GPT-2 Medium", "size": "1.5GB"},
                {"id": "distilgpt2", "name": "DistilGPT-2 (Rápido)", "size": "300MB"},
                {"id": "EleutherAI/gpt-neo-125M", "name": "GPT-Neo 125M", "size": "500MB"},
            ],
            "multilingual": [
                {"id": "bigscience/bloomz-560m", "name": "BLOOMZ-560M (46 idiomas) ⭐", "size": "2.5GB"},
                {"id": "bigscience/bloom-560m", "name": "BLOOM-560M", "size": "2.5GB"},
            ],
            "local": []  # Se llenará con modelos locales
        },
        "claude": [
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet (Latest) ⭐", "cost": "$3/1M tokens"},
            {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "cost": "$15/1M tokens"},
            {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet", "cost": "$3/1M tokens"},
            {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku", "cost": "$0.25/1M tokens"},
        ],
        "openai": [
            {"id": "gpt-4o-mini", "name": "GPT-4o Mini ⭐", "cost": "$0.15/1M tokens"},
            {"id": "gpt-4o", "name": "GPT-4o", "cost": "$2.50/1M tokens"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "cost": "$10/1M tokens"},
            {"id": "gpt-4", "name": "GPT-4", "cost": "$30/1M tokens"},
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "cost": "$0.50/1M tokens"},
        ]
    }
    
    # Agregar modelos entrenados localmente
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    model_dir = BASE_DIR / "model_llm"
    if model_dir.exists():
        local_models = []
        for model_path in model_dir.iterdir():
            if model_path.is_dir() and (model_path / "config.json").exists():
                local_models.append({
                    "id": str(model_path.relative_to(BASE_DIR)),
                    "name": f"🎓 {model_path.name} (Entrenado)",
                    "size": "Local"
                })
        if local_models:
            all_models["huggingface"]["local"] = local_models
    
    # Si se especifica provider, retornar solo ese
    if provider:
        return {
            "provider": provider,
            "models": all_models.get(provider, [])
        }
    
    return {"providers": all_models}


@router.post("/providers/switch")
async def switch_provider(
    data: ProviderSwitch,
    current_user=Depends(get_current_admin_user)
):
    """
    Cambia el provider y modelo activo.
    Actualiza config.json, variables de entorno y reinicia la API automáticamente.
    Requiere permisos de administrador.
    """
    import json
    import os
    import subprocess
    import signal
    
    allowed_providers = ["huggingface", "claude", "openai"]
    
    if data.provider not in allowed_providers:
        raise HTTPException(
            status_code=400,
            detail=f"Provider no válido. Permitidos: {', '.join(allowed_providers)}"
        )
    
    # Leer config actual para verificar si hay keys guardadas
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    config_path = BASE_DIR / "config" / "config.json"
    existing_config = {}
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                existing_config = json.load(f)
        except Exception:
            pass
    
    # Validar API keys: requeridas si no hay una guardada previamente
    if data.provider == "claude":
        has_saved_key = existing_config.get("anthropic_api_key")
        if not data.api_key and not has_saved_key:
            raise HTTPException(
                status_code=400,
                detail="La API key de Anthropic es requerida para usar Claude"
            )
    if data.provider == "openai":
        has_saved_key = existing_config.get("openai_api_key")
        if not data.api_key and not has_saved_key:
            raise HTTPException(
                status_code=400,
                detail="La API key de OpenAI es requerida"
            )
    
    # Actualizar config.json
    BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
    config_path = BASE_DIR / "config" / "config.json"
    
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
    else:
        config = {}
    
    # Normalizar provider a formato interno
    provider_internal = {
        "huggingface": "hf",
        "claude": "claude",
        "openai": "openai"
    }
    
    config["provider"] = provider_internal.get(data.provider, data.provider)
    config["model_name"] = data.model
    
    # Actualizar configuraciones según provider (CONSERVAR las keys existentes)
    if data.provider == "claude":
        if data.api_key:  # Solo actualizar si se proporciona
            config["anthropic_api_key"] = data.api_key
        if data.api_version:
            config["anthropic_api_version"] = data.api_version
        if data.max_tokens:
            config["max_tokens"] = data.max_tokens
    elif data.provider == "openai":
        if data.api_key:  # Solo actualizar si se proporciona
            config["openai_api_key"] = data.api_key
        if data.organization_id:
            config["openai_organization_id"] = data.organization_id
        if data.base_url:
            config["openai_base_url"] = data.base_url
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    # Actualizar variables de entorno para el proceso actual
    if data.api_key:
        if data.provider == "claude":
            os.environ["ANTHROPIC_API_KEY"] = data.api_key
        elif data.provider == "openai":
            os.environ["OPENAI_API_KEY"] = data.api_key
    
    # Reiniciar la API en segundo plano usando subprocess
    # Buscar el proceso de la API principal (puerto 8000)
    try:
        # Encontrar el PID del proceso uvicorn app.main:app
        result = subprocess.run(
            ["pgrep", "-f", "uvicorn app.main:app"],
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            pid = int(result.stdout.strip().split()[0])
            # Enviar señal de recarga (SIGHUP) en lugar de matar el proceso
            os.kill(pid, signal.SIGHUP)
            message = f"✅ Provider cambiado a {data.provider} con modelo {data.model}. API reiniciada automáticamente."
        else:
            message = f"✅ Provider cambiado a {data.provider} con modelo {data.model}. Por favor reinicia la API manualmente."
    except Exception as e:
        message = f"✅ Provider cambiado a {data.provider} con modelo {data.model}. Reinicio automático falló: {str(e)}. Por favor reinicia manualmente."
    
    return {
        "message": message,
        "provider": data.provider,
        "model": data.model,
        "restart_attempted": True
    }



# ===== ENDPOINTS STATS =====

@router.get("/stats")
async def get_stats(current_user=Depends(get_current_admin_user)):
    """
    Obtiene estadísticas generales del sistema.
    Requiere permisos de administrador.
    """
    from ...db.sqlite import USER_DB_PATH, FEEDBACK_DB_PATH
    import os
    
    stats = {}
    
    # Estadísticas de usuarios
    with sqlite3.connect(str(USER_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        stats["total_users"] = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
        stats["total_admins"] = cursor.fetchone()[0]
    
    # Estadísticas de feedback
    with sqlite3.connect(str(FEEDBACK_DB_PATH)) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM feedback")
        stats["total_feedback"] = cursor.fetchone()[0]
    
    # Tamaños de bases de datos
    stats["db_sizes"] = {
        "users_db": os.path.getsize(USER_DB_PATH) if USER_DB_PATH.exists() else 0,
        "feedback_db": os.path.getsize(FEEDBACK_DB_PATH) if FEEDBACK_DB_PATH.exists() else 0
    }
    
    # Provider actual
    from ...core.settings import settings
    stats["current_provider"] = settings.PROVIDER
    stats["current_model"] = getattr(settings, 'MODEL_NAME', settings.DEFAULT_MODEL)
    
    return stats
