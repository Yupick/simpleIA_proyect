#!/usr/bin/env python3
"""
llm_client.py
-------------
Cliente web para el sistema LLM con interfaz de chat y registro de usuarios,
usando HTML y JavaScript para mantener la conversación en una sola página.
"""

import os
from pathlib import Path
import uvicorn
import requests
import jwt
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from app.core.settings import settings

# Importar routers de API para funcionalidad del chat
from app.api.routers.user.chat import router as chat_api_router
from app.api.routers.user.products import router as products_api_router
from app.api.routers.user.personal import router as personal_api_router

load_dotenv()

# Definir la ruta base (este archivo está en app/)
BASE_DIR = Path(__file__).resolve().parent.parent
static_dir = BASE_DIR / "static"
if not static_dir.exists():
    os.makedirs(static_dir)
templates_dir = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

app = FastAPI(title="LLM Chat Client with Registration")

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# URL base de la API
API_URL = "http://localhost:8000"

def get_current_user_from_cookies(request: Request):
    """Decodifica el token JWT de la cookie y retorna la info del usuario."""
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username = payload.get("sub")
        is_admin = payload.get("is_admin", False)
        role = payload.get("role", "user")
        user_id = payload.get("user_id")
        
        if username:
            return {
                "username": username, 
                "is_admin": is_admin,
                "role": role,
                "id": user_id  # Agregar 'id' que es lo que esperan los endpoints
            }
    except Exception as e:
        pass
    return None

# Alias para compatibilidad
decode_token_from_cookie = get_current_user_from_cookies

@app.get("/api/system-info")
async def get_system_info():
    """Obtiene información del sistema actual (provider, modelo)."""
    try:
        import json
        from pathlib import Path
        
        BASE_DIR = Path(__file__).resolve().parent.parent
        config_path = BASE_DIR / "config" / "config.json"
        
        provider = "huggingface"
        model = "gpt2"
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    provider_raw = config.get("provider", "hf")
                    
                    # Mapear a nombres legibles
                    provider_map = {
                        "hf": "HuggingFace",
                        "huggingface": "HuggingFace",
                        "claude": "Claude (Anthropic)",
                        "openai": "OpenAI"
                    }
                    provider = provider_map.get(provider_raw, provider_raw)
                    model = config.get("model_name", config.get("selected_model", model))
            except Exception as e:
                print(f"Error leyendo config: {e}")
        
        return JSONResponse(content={
            "provider": provider,
            "model": model
        })
    except Exception as e:
        return JSONResponse(content={
            "provider": "Error",
            "model": str(e)
        }, status_code=500)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    user = decode_token_from_cookie(request)
    # Inicialmente el chat está vacío; se actualizará con JS
    return templates.TemplateResponse("index.html", {"request": request, "user": user, "messages": []})

@app.post("/predict", response_class=JSONResponse)
async def predict(request: Request):
    """Proxy endpoint que acepta JSON y reenvía a la API."""
    try:
        body = await request.json()
        prompt = body.get("prompt")
        if not prompt:
            return JSONResponse(content={"error": "prompt is required"}, status_code=400)
        
        # Preparar payload con todos los parámetros
        payload = {
            "prompt": prompt,
            "max_length": body.get("max_length", 50),
            "num_return_sequences": body.get("num_return_sequences", 1),
            "temperature": body.get("temperature", 0.7),
            "stream": body.get("stream", False)
        }
        
        headers = {}
        token = request.cookies.get("access_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        response = requests.post(f"{API_URL}/predict", json=payload, headers=headers)
        response.raise_for_status()
        
        # Si es streaming, retornar el stream directamente
        if payload.get("stream"):
            return StreamingResponse(
                response.iter_content(chunk_size=1024),
                media_type="text/event-stream"
            )
        
        data = response.json()
        generated_text = data.get("generated_text", "No response received")
        return JSONResponse(content={"generated_text": generated_text})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)

@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    user = decode_token_from_cookie(request)
    return templates.TemplateResponse("login.html", {"request": request, "user": user})

@app.post("/login")
async def login_post(username: str = Form(...), password: str = Form(...)):
    """
    Login con redirección inteligente según role:
    - superadmin → /admin/dashboard
    - user → /user/dashboard
    """
    payload = {"username": username, "password": password}
    try:
        response = requests.post(f"{API_URL}/auth/login", data=payload)
        response.raise_for_status()
        data = response.json()
        access_token = data.get("access_token")
        role = data.get("role", "user")  # Obtener role del response
        is_admin = data.get("is_admin", False)
        
        if not access_token:
            return HTMLResponse("Error: No token obtained", status_code=400)
        
        # Redirigir según role
        if role == "superadmin":
            redirect_url = "/admin/dashboard"
        else:
            redirect_url = "/user/dashboard"
        
        redirect = RedirectResponse(url=redirect_url, status_code=302)
        secure = os.getenv("ENVIRONMENT", "development") == "production"
        redirect.set_cookie(
            key="access_token", 
            value=access_token, 
            httponly=True, 
            secure=secure, 
            samesite="lax"
        )
        return redirect
    except Exception as e:
        return HTMLResponse(f"Error during login: {e}", status_code=400)

@app.get("/logout")
async def logout():
    redirect = RedirectResponse(url="/", status_code=302)
    secure = os.getenv("ENVIRONMENT", "development") == "production"
    redirect.delete_cookie("access_token", secure=secure, samesite="lax")
    return redirect

@app.get("/register", response_class=HTMLResponse)
async def register_get(request: Request):
    user = decode_token_from_cookie(request)
    return templates.TemplateResponse("register.html", {"request": request, "user": user})

@app.post("/register", response_class=HTMLResponse)
async def register_post(username: str = Form(...), password: str = Form(...)):
    payload = {"username": username, "password": password}
    try:
        response = requests.post(f"{API_URL}/auth/register", json=payload)
        response.raise_for_status()
        return HTMLResponse("Registration successful. Now you can <a href='/login'>login</a>.")
    except Exception as e:
        return HTMLResponse(f"Registration error: {e}", status_code=400)

@app.post("/feedback", response_class=JSONResponse)
async def feedback_proxy(request: Request):
    """Proxy endpoint para feedback que incluye autenticación."""
    try:
        body = await request.json()
        text = body.get("text")
        if not text:
            return JSONResponse(content={"error": "text is required"}, status_code=400)
        
        headers = {}
        token = request.cookies.get("access_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        response = requests.post(f"{API_URL}/feedback", json={"text": text}, headers=headers)
        response.raise_for_status()
        
        return JSONResponse(content=response.json())
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)


# ===== RUTAS ADMIN =====

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard_page(request: Request):
    """Dashboard principal admin - Redirige a /admin/dashboard."""
    return RedirectResponse(url="/admin/dashboard", status_code=302)


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard_main(request: Request):
    """Dashboard principal admin."""
    user = decode_token_from_cookie(request)
    if not user or user.get("role") != "superadmin":
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "user": user,
        "active_tab": "dashboard"
    })


# ===== RUTAS USER =====

@app.get("/user", response_class=HTMLResponse)
async def user_root(request: Request):
    """Redirige /user a /user/dashboard."""
    return RedirectResponse(url="/user/dashboard", status_code=302)


@app.get("/user/dashboard", response_class=HTMLResponse)
async def user_dashboard_page(request: Request):
    """Dashboard principal de usuario regular."""
    user = decode_token_from_cookie(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("user/dashboard.html", {
        "request": request,
        "user": user
    })


@app.get("/user/commercial/products", response_class=HTMLResponse)
async def user_commercial_products(request: Request):
    """Página de gestión de productos del usuario."""
    user = decode_token_from_cookie(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("user/commercial/products.html", {"request": request, "user": user})


@app.get("/user/commercial/whatsapp", response_class=HTMLResponse)
async def user_commercial_whatsapp(request: Request):
    """Página de gestión de WhatsApp del usuario."""
    user = decode_token_from_cookie(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    # TODO: Crear template user/commercial/whatsapp.html
    return HTMLResponse("<h1>WhatsApp (En desarrollo)</h1>")


@app.get("/user/commercial/analytics", response_class=HTMLResponse)
async def user_commercial_analytics(request: Request):
    """Página de analytics comerciales del usuario."""
    user = decode_token_from_cookie(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    # TODO: Crear template user/commercial/analytics.html
    return HTMLResponse("<h1>Mis Métricas (En desarrollo)</h1>")


@app.get("/user/personal/calendar", response_class=HTMLResponse)
async def user_personal_calendar(request: Request):
    """Página de calendario del usuario."""
    user = decode_token_from_cookie(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("user/personal/calendar.html", {
        "request": request,
        "user": user
    })


@app.get("/user/personal/tasks", response_class=HTMLResponse)
async def user_personal_tasks(request: Request):
    """Página de tareas del usuario."""
    user = decode_token_from_cookie(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("user/personal/tasks.html", {
        "request": request,
        "user": user
    })


@app.get("/user/personal/reminders", response_class=HTMLResponse)
async def user_personal_reminders(request: Request):
    """Página de recordatorios del usuario."""
    user = decode_token_from_cookie(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    # TODO: Crear template user/personal/reminders.html
    return HTMLResponse("<h1>Mis Recordatorios (En desarrollo)</h1>")


@app.get("/user/chat", response_class=HTMLResponse)
async def user_chat(request: Request):
    """Página de chat con asistentes del usuario."""
    user = decode_token_from_cookie(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    
    return templates.TemplateResponse("user/chat.html", {
        "request": request,
        "user": user
    })


# ===== RUTAS ADMIN (continuación) =====


@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page(request: Request):
    """Página de gestión de usuarios (admin)."""
    user = decode_token_from_cookie(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("admin_users.html", {
        "request": request,
        "user": user,
        "active_tab": "users"
    })


@app.get("/admin/config", response_class=HTMLResponse)
async def admin_config_page(request: Request):
    """Página de configuración del sistema (admin)."""
    user = decode_token_from_cookie(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("admin_config.html", {
        "request": request,
        "user": user,
        "active_tab": "config"
    })


@app.get("/admin/feedback", response_class=HTMLResponse)
async def admin_feedback_page(request: Request):
    """Página de gestión de feedback (admin)."""
    user = decode_token_from_cookie(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("admin_feedback.html", {
        "request": request,
        "user": user,
        "active_tab": "feedback"
    })


@app.get("/admin/providers", response_class=HTMLResponse)
async def admin_providers_page(request: Request):
    """Página de gestión de providers (admin)."""
    user = decode_token_from_cookie(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("admin_providers.html", {
        "request": request,
        "user": user,
        "active_tab": "providers"
    })


@app.get("/admin/stats", response_class=HTMLResponse)
async def admin_stats_page(request: Request):
    """Página de estadísticas detalladas (admin)."""
    user = decode_token_from_cookie(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("admin_stats.html", {
        "request": request,
        "user": user,
        "active_tab": "stats"
    })


@app.get("/admin/training", response_class=HTMLResponse)
async def admin_training_page(request: Request):
    """Página de entrenamiento del modelo (admin)."""
    user = decode_token_from_cookie(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("admin_training.html", {
        "request": request,
        "user": user,
        "active_tab": "training"
    })


# ===== PROXIES API ADMIN (usando prefijo /api) =====

@app.api_route("/api/admin/stats", methods=["GET"], response_class=JSONResponse)
async def admin_stats_proxy(request: Request):
    """Proxy para obtener estadísticas del sistema."""
    user = decode_token_from_cookie(request)
    if not user or not user.get("is_admin"):
        return JSONResponse(content={"error": "Unauthorized"}, status_code=403)
    
    try:
        token = request.cookies.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{API_URL}/admin/stats", headers=headers)
        response.raise_for_status()
        return JSONResponse(content=response.json())
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)


@app.api_route("/api/admin/users", methods=["GET"], response_class=JSONResponse)
async def admin_users_proxy(request: Request, page: int = 1, limit: int = 20):
    """Proxy para listar usuarios."""
    user = decode_token_from_cookie(request)
    if not user or not user.get("is_admin"):
        return JSONResponse(content={"error": "Unauthorized"}, status_code=403)
    
    try:
        token = request.cookies.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{API_URL}/admin/users?page={page}&limit={limit}", headers=headers)
        response.raise_for_status()
        return JSONResponse(content=response.json())
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)


@app.api_route("/api/admin/users/{user_id}/role", methods=["POST"], response_class=JSONResponse)
async def admin_user_role_proxy(request: Request, user_id: int):
    """Proxy para actualizar rol de usuario."""
    user = decode_token_from_cookie(request)
    if not user or not user.get("is_admin"):
        return JSONResponse(content={"error": "Unauthorized"}, status_code=403)
    
    try:
        body = await request.json()
        token = request.cookies.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{API_URL}/admin/users/{user_id}/role", json=body, headers=headers)
        response.raise_for_status()
        return JSONResponse(content=response.json())
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)


@app.api_route("/api/admin/users/{user_id}", methods=["DELETE"], response_class=JSONResponse)
async def admin_user_delete_proxy(request: Request, user_id: int):
    """Proxy para eliminar usuario."""
    user = decode_token_from_cookie(request)
    if not user or not user.get("is_admin"):
        return JSONResponse(content={"error": "Unauthorized"}, status_code=403)
    
    try:
        token = request.cookies.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.delete(f"{API_URL}/admin/users/{user_id}", headers=headers)
        response.raise_for_status()
        return JSONResponse(content=response.json())
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)


@app.api_route("/api/admin/feedback", methods=["GET"], response_class=JSONResponse)
async def admin_feedback_proxy(request: Request, search: str = ""):
    """Proxy para listar feedback."""
    user = decode_token_from_cookie(request)
    if not user or not user.get("is_admin"):
        return JSONResponse(content={"error": "Unauthorized"}, status_code=403)
    
    try:
        token = request.cookies.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{API_URL}/admin/feedback"
        if search:
            url += f"?search={search}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return JSONResponse(content=response.json())
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)


@app.api_route("/api/admin/feedback/{feedback_id}", methods=["DELETE"], response_class=JSONResponse)
async def admin_feedback_delete_proxy(request: Request, feedback_id: int):
    """Proxy para eliminar feedback."""
    user = decode_token_from_cookie(request)
    if not user or not user.get("is_admin"):
        return JSONResponse(content={"error": "Unauthorized"}, status_code=403)
    
    try:
        token = request.cookies.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.delete(f"{API_URL}/admin/feedback/{feedback_id}", headers=headers)
        response.raise_for_status()
        return JSONResponse(content=response.json())
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)


@app.api_route("/api/admin/config", methods=["GET", "POST"], response_class=JSONResponse)
async def admin_config_api_proxy(request: Request):
    """Proxy para obtener/actualizar configuración."""
    user = decode_token_from_cookie(request)
    if not user or not user.get("is_admin"):
        return JSONResponse(content={"error": "Unauthorized"}, status_code=403)
    
    try:
        token = request.cookies.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        if request.method == "GET":
            response = requests.get(f"{API_URL}/admin/config", headers=headers)
        else:  # POST
            body = await request.json()
            response = requests.post(f"{API_URL}/admin/config", json=body, headers=headers)
        
        response.raise_for_status()
        return JSONResponse(content=response.json())
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)


@app.api_route("/api/admin/config/logo", methods=["POST"], response_class=JSONResponse)
async def admin_config_logo_proxy(request: Request):
    """Proxy para subir logo."""
    user = decode_token_from_cookie(request)
    if not user or not user.get("is_admin"):
        return JSONResponse(content={"error": "Unauthorized"}, status_code=403)
    
    try:
        # Reenviar el multipart/form-data al API
        token = request.cookies.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        
        form = await request.form()
        files = {}
        if "logo" in form:
            logo_file = form["logo"]
            files["logo"] = (logo_file.filename, await logo_file.read(), logo_file.content_type)
        
        response = requests.post(f"{API_URL}/admin/config/logo", files=files, headers=headers)
        response.raise_for_status()
        return JSONResponse(content=response.json())
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)


@app.api_route("/admin/providers/current", methods=["GET"], response_class=JSONResponse)
async def admin_providers_current_proxy(request: Request):
    """Proxy para obtener el provider actual."""
    user = decode_token_from_cookie(request)
    if not user or not user.get("is_admin"):
        return JSONResponse(content={"error": "Unauthorized"}, status_code=403)
    
    try:
        token = request.cookies.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{API_URL}/admin/providers/current", headers=headers)
        response.raise_for_status()
        return JSONResponse(content=response.json())
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                error_msg = error_detail.get('detail', str(e))
            except:
                error_msg = e.response.text or str(e)
        print(f"Error en providers/current proxy: {error_msg}")
        return JSONResponse(content={"error": error_msg}, status_code=500)
    except Exception as e:
        print(f"Error inesperado en providers/current proxy: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.api_route("/admin/providers/models", methods=["GET"], response_class=JSONResponse)
async def admin_providers_models_proxy(request: Request):
    """Proxy para obtener los modelos disponibles por provider."""
    user = decode_token_from_cookie(request)
    if not user or not user.get("is_admin"):
        return JSONResponse(content={"error": "Unauthorized"}, status_code=403)
    
    try:
        token = request.cookies.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        # Pasar los query params (provider)
        provider = request.query_params.get("provider")
        url = f"{API_URL}/admin/providers/models"
        if provider:
            url += f"?provider={provider}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return JSONResponse(content=response.json())
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                error_msg = error_detail.get('detail', str(e))
            except:
                error_msg = e.response.text or str(e)
        print(f"Error en providers/models proxy: {error_msg}")
        return JSONResponse(content={"error": error_msg}, status_code=500)
    except Exception as e:
        print(f"Error inesperado en providers/models proxy: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.api_route("/admin/providers/switch", methods=["POST"], response_class=JSONResponse)
async def admin_providers_switch_proxy(request: Request):
    """Proxy para cambiar provider."""
    user = decode_token_from_cookie(request)
    if not user or not user.get("is_admin"):
        return JSONResponse(content={"error": "Unauthorized"}, status_code=403)
    
    try:
        body = await request.json()
        token = request.cookies.get("access_token")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        response = requests.post(f"{API_URL}/admin/providers/switch", json=body, headers=headers)
        response.raise_for_status()
        return JSONResponse(content=response.json())
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                error_msg = error_detail.get('detail', str(e))
            except:
                error_msg = e.response.text or str(e)
        print(f"Error en providers/switch proxy: {error_msg}")
        return JSONResponse(content={"error": error_msg, "detail": error_msg}, status_code=500)
    except Exception as e:
        print(f"Error inesperado en providers/switch proxy: {str(e)}")
        return JSONResponse(content={"error": str(e), "detail": str(e)}, status_code=500)


# ===== PROXIES TRAINING API =====

@app.api_route("/training/{path:path}", methods=["GET", "POST", "DELETE"])
async def training_proxy(request: Request, path: str):
    """Proxy para todos los endpoints de training."""
    try:
        # Verificar autenticación
        user = decode_token_from_cookie(request)
        if not user:
            return JSONResponse(content={"error": "Unauthorized"}, status_code=401)
        
        token = request.cookies.get("access_token")
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{API_URL}/training/{path}"
        
        # Manejar diferentes métodos HTTP
        if request.method == "GET":
            response = requests.get(url, headers=headers, params=request.query_params)
        elif request.method == "POST":
            # Verificar si es FormData (multipart) o JSON
            content_type = request.headers.get("content-type", "")
            if "multipart/form-data" in content_type:
                # Para uploads de archivos
                form = await request.form()
                files = {}
                data = {}
                for key, value in form.items():
                    if hasattr(value, 'read'):  # Es un archivo
                        files[key] = (value.filename, await value.read(), value.content_type)
                    else:
                        data[key] = value
                response = requests.post(url, headers={"Authorization": f"Bearer {token}"}, files=files, data=data)
            else:
                # JSON
                body = await request.json() if await request.body() else {}
                headers["Content-Type"] = "application/json"
                response = requests.post(url, json=body, headers=headers)
        elif request.method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            return JSONResponse(content={"error": "Method not allowed"}, status_code=405)
        
        response.raise_for_status()
        return JSONResponse(content=response.json(), status_code=response.status_code)
        
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        status_code = 500
        if hasattr(e, 'response') and e.response is not None:
            status_code = e.response.status_code
            try:
                error_detail = e.response.json()
                error_msg = error_detail.get('detail', str(e))
            except:
                error_msg = e.response.text or str(e)
        print(f"Error en training proxy: {error_msg}")
        return JSONResponse(content={"error": error_msg, "detail": error_msg}, status_code=status_code)
    except Exception as e:
        print(f"Error inesperado en training proxy: {str(e)}")
        return JSONResponse(content={"error": str(e), "detail": str(e)}, status_code=500)


# ============================================================================
# MONTAR ROUTERS DE API PARA FUNCIONALIDAD DEL CHAT
# ============================================================================

# Montar routers de API del usuario (chat, productos, personal)
app.include_router(chat_api_router, prefix="/api/user")
app.include_router(products_api_router, prefix="/api/user")
app.include_router(personal_api_router, prefix="/api/user")


# ============================================================================
# ENDPOINTS DE API PARA TEMPLATES DE USUARIO
# ============================================================================

@app.get("/api/user/dashboard")
async def get_user_dashboard(request: Request):
    """Obtiene datos para el dashboard del usuario."""
    user = get_current_user_from_cookies(request)
    if not user:
        return JSONResponse(content={"error": "No autenticado"}, status_code=401)
    
    try:
        from app.db import products as products_db
        from app.db import personal as personal_db
        from app.db import conversations as conversations_db
        
        user_id = user['id']
        
        # Contar productos activos
        products = products_db.list_products(user_id)
        products_count = len([p for p in products if not p.get('deleted_at')])
        
        # Contar citas próximas (próximos 7 días)
        today = datetime.now().strftime("%Y-%m-%d")
        next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        appointments = personal_db.list_appointments(
            user_id=user_id,
            start_date=today,
            end_date=next_week,
            status="scheduled"
        )
        
        # Contar tareas pendientes
        tasks = personal_db.list_tasks(user_id, status="pending")
        
        # Contar conversaciones (últimas 30 días)
        conversations = conversations_db.list_conversations(user_id, limit=50)
        recent_conversations = [c for c in conversations if c.get('updated_at')]
        
        # Obtener tareas recientes (máximo 5)
        recent_tasks = sorted(
            [t for t in tasks if t.get('created_at')],
            key=lambda x: x['created_at'],
            reverse=True
        )[:5]
        
        # Obtener citas próximas (máximo 3)
        upcoming_appointments = sorted(
            appointments,
            key=lambda x: x['start_datetime']
        )[:3]
        
        # Actividad reciente
        recent_activity = []
        
        # Agregar tareas recientes
        for task in recent_tasks[:3]:
            created = datetime.fromisoformat(task['created_at'])
            time_ago = get_time_ago(created)
            recent_activity.append({
                'type': 'task',
                'title': f"Tarea creada: {task['title']}",
                'time_ago': time_ago
            })
        
        # Agregar citas recientes
        for apt in appointments[:2]:
            start_dt = datetime.fromisoformat(apt['start_datetime'])
            time_ago = get_time_ago(start_dt)
            recent_activity.append({
                'type': 'appointment',
                'title': f"Cita agendada: {apt['title']}",
                'time_ago': time_ago
            })
        
        # Ordenar por más reciente
        recent_activity.sort(key=lambda x: x['time_ago'])
        
        return JSONResponse(content={
            "products_count": products_count,
            "upcoming_appointments": len(appointments),
            "pending_tasks": len(tasks),
            "conversations_count": len(recent_conversations),
            "tasks": [
                {
                    "id": t['id'],
                    "title": t['title'],
                    "due_date": t.get('due_date'),
                    "priority": t.get('priority', 'medium'),
                    "status": t.get('status', 'pending')
                }
                for t in recent_tasks
            ],
            "appointments": [
                {
                    "id": a['id'],
                    "title": a['title'],
                    "start_datetime": a['start_datetime'],
                    "location": a.get('location')
                }
                for a in upcoming_appointments
            ],
            "recent_activity": recent_activity[:5]
        })
    except Exception as e:
        print(f"Error en dashboard: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/user/analytics")
async def get_user_analytics(request: Request, days: int = 7):
    """Obtiene datos de analytics del usuario."""
    user = get_current_user_from_cookies(request)
    if not user:
        return JSONResponse(content={"error": "No autenticado"}, status_code=401)
    
    try:
        from app.db import personal as personal_db
        from app.db import products as products_db
        from app.db import conversations as conversations_db
        
        user_id = user['id']
        
        # Tareas completadas en el período
        all_tasks = personal_db.list_tasks(user_id)
        completed_tasks = [
            t for t in all_tasks 
            if t.get('status') == 'completed' and t.get('completed_at')
        ]
        
        # Filtrar por período
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_completed = [
            t for t in completed_tasks
            if datetime.fromisoformat(t['completed_at']) >= cutoff_date
        ]
        
        # Citas en el período
        today = datetime.now().strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        appointments = personal_db.list_appointments(
            user_id=user_id,
            start_date=today,
            end_date=end_date
        )
        
        # Productos activos
        products = products_db.list_products(user_id)
        active_products = [p for p in products if not p.get('deleted_at')]
        
        # Conversaciones
        conversations = conversations_db.list_conversations(user_id, limit=100)
        
        # Datos para gráficos
        tasks_by_day = generate_tasks_chart_data(recent_completed, days)
        appointments_by_week = generate_appointments_chart_data(appointments)
        assistant_usage = calculate_assistant_usage(conversations)
        
        return JSONResponse(content={
            "tasks_completed": len(recent_completed),
            "appointments_total": len(appointments),
            "products_total": len(active_products),
            "conversations_total": len(conversations),
            "tasks_by_day": tasks_by_day,
            "appointments_by_week": appointments_by_week,
            "assistant_usage": assistant_usage,
            "recent_activity": generate_recent_activity(all_tasks, appointments, products)
        })
    except Exception as e:
        print(f"Error en analytics: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/user/whatsapp/status")
async def get_whatsapp_status(request: Request):
    """Obtiene el estado de conexión de WhatsApp."""
    user = get_current_user_from_cookies(request)
    if not user:
        return JSONResponse(content={"error": "No autenticado"}, status_code=401)
    
    # TODO: Implementar conexión real con WhatsApp
    return JSONResponse(content={
        "connected": False,
        "phone_number": None,
        "connected_since": None
    })


@app.post("/api/user/whatsapp/generate-qr")
async def generate_whatsapp_qr(request: Request):
    """Genera código QR para vincular WhatsApp."""
    user = get_current_user_from_cookies(request)
    if not user:
        return JSONResponse(content={"error": "No autenticado"}, status_code=401)
    
    # TODO: Implementar generación de QR real
    return JSONResponse(content={
        "success": True,
        "qr_code": "data:image/png;base64,..."
    })


@app.post("/api/user/whatsapp/disconnect")
async def disconnect_whatsapp(request: Request):
    """Desconecta WhatsApp."""
    user = get_current_user_from_cookies(request)
    if not user:
        return JSONResponse(content={"error": "No autenticado"}, status_code=401)
    
    # TODO: Implementar desconexión real
    return JSONResponse(content={"success": True})


@app.get("/api/user/whatsapp/settings")
async def get_whatsapp_settings(request: Request):
    """Obtiene configuración de WhatsApp."""
    user = get_current_user_from_cookies(request)
    if not user:
        return JSONResponse(content={"error": "No autenticado"}, status_code=401)
    
    # TODO: Cargar desde DB
    return JSONResponse(content={
        "task_notifications": False,
        "appointment_notifications": True,
        "auto_responses": False,
        "confirm_before_send": True
    })


@app.post("/api/user/whatsapp/settings")
async def save_whatsapp_settings(request: Request):
    """Guarda configuración de WhatsApp."""
    user = get_current_user_from_cookies(request)
    if not user:
        return JSONResponse(content={"error": "No autenticado"}, status_code=401)
    
    data = await request.json()
    # TODO: Guardar en DB
    return JSONResponse(content={"success": True})


@app.get("/api/user/whatsapp/logs")
async def get_whatsapp_logs(request: Request):
    """Obtiene logs de mensajes de WhatsApp."""
    user = get_current_user_from_cookies(request)
    if not user:
        return JSONResponse(content={"error": "No autenticado"}, status_code=401)
    
    # TODO: Cargar desde DB
    return JSONResponse(content=[])


@app.get("/api/user/reminders/preferences")
async def get_reminder_preferences(request: Request):
    """Obtiene preferencias de recordatorios."""
    user = get_current_user_from_cookies(request)
    if not user:
        return JSONResponse(content={"error": "No autenticado"}, status_code=401)
    
    # TODO: Cargar desde DB
    return JSONResponse(content={
        "email_enabled": True,
        "whatsapp_enabled": False,
        "browser_enabled": False,
        "task_timing": 60,
        "appointment_timing": 15
    })


@app.post("/api/user/reminders/preferences")
async def save_reminder_preferences(request: Request):
    """Guarda preferencias de recordatorios."""
    user = get_current_user_from_cookies(request)
    if not user:
        return JSONResponse(content={"error": "No autenticado"}, status_code=401)
    
    data = await request.json()
    # TODO: Guardar en DB
    return JSONResponse(content={"success": True})


@app.get("/api/user/reminders/history")
async def get_reminder_history(request: Request):
    """Obtiene historial de recordatorios."""
    user = get_current_user_from_cookies(request)
    if not user:
        return JSONResponse(content={"error": "No autenticado"}, status_code=401)
    
    # TODO: Cargar desde DB
    return JSONResponse(content=[])


# ============================================================================
# FUNCIONES AUXILIARES PARA ANALYTICS
# ============================================================================

def get_time_ago(dt: datetime) -> str:
    """Calcula tiempo transcurrido en formato legible."""
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"Hace {diff.days} día{'s' if diff.days > 1 else ''}"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f"Hace {hours} hora{'s' if hours > 1 else ''}"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f"Hace {minutes} minuto{'s' if minutes > 1 else ''}"
    else:
        return "Hace un momento"


def generate_tasks_chart_data(tasks, days):
    """Genera datos para gráfico de tareas por día."""
    # Crear diccionario con últimos N días
    data = {}
    for i in range(days):
        date = (datetime.now() - timedelta(days=days-i-1)).strftime("%Y-%m-%d")
        data[date] = 0
    
    # Contar tareas por día
    for task in tasks:
        if task.get('completed_at'):
            date = task['completed_at'][:10]
            if date in data:
                data[date] += 1
    
    return {
        "labels": [datetime.fromisoformat(d).strftime("%d/%m") for d in data.keys()],
        "values": list(data.values())
    }


def generate_appointments_chart_data(appointments):
    """Genera datos para gráfico de citas por semana."""
    # Simplificado: contar por semana del mes
    weeks = {"Semana 1": 0, "Semana 2": 0, "Semana 3": 0, "Semana 4": 0}
    
    for apt in appointments:
        date = datetime.fromisoformat(apt['start_datetime'])
        week = (date.day - 1) // 7 + 1
        week_label = f"Semana {min(week, 4)}"
        if week_label in weeks:
            weeks[week_label] += 1
    
    return {
        "labels": list(weeks.keys()),
        "values": list(weeks.values())
    }


def calculate_assistant_usage(conversations):
    """Calcula uso de asistentes."""
    personal_count = 0
    commercial_count = 0
    
    for conv in conversations:
        if conv.get('assistant_type') == 'personal':
            personal_count += 1
        elif conv.get('assistant_type') == 'commercial':
            commercial_count += 1
    
    return {
        "personal": personal_count,
        "commercial": commercial_count
    }


def generate_recent_activity(tasks, appointments, products):
    """Genera lista de actividad reciente."""
    activity = []
    
    # Tareas recientes
    for task in sorted(tasks, key=lambda x: x.get('created_at', ''), reverse=True)[:3]:
        if task.get('created_at'):
            created = datetime.fromisoformat(task['created_at'])
            activity.append({
                'type': 'task',
                'title': f"Tarea: {task['title']}",
                'time_ago': get_time_ago(created)
            })
    
    # Citas recientes
    for apt in sorted(appointments, key=lambda x: x.get('created_at', ''), reverse=True)[:2]:
        if apt.get('created_at'):
            created = datetime.fromisoformat(apt['created_at'])
            activity.append({
                'type': 'appointment',
                'title': f"Cita: {apt['title']}",
                'time_ago': get_time_ago(created)
            })
    
    return sorted(activity, key=lambda x: x['time_ago'])[:5]


# ============================================================================
# STARTUP: INICIALIZACIÓN DE BASES DE DATOS
# ============================================================================

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa las bases de datos y el modelo LLM al iniciar el servidor."""
    # Importar funciones de inicialización
    from app.db.sqlite import init_user_db
    from app.db.products import init_products_db
    from app.db.personal import init_personal_db
    from app.db.conversations import init_conversations_db
    from app.models.model_manager import load_model
    
    # Inicializar bases de datos
    print("🔧 Inicializando bases de datos...")
    init_user_db()
    init_products_db()
    init_personal_db()
    init_conversations_db()
    print("✅ Bases de datos inicializadas")
    
    # Cargar modelo LLM
    print("🤖 Cargando modelo LLM...")
    try:
        load_model()
        print("✅ Modelo LLM cargado correctamente")
    except Exception as e:
        print(f"⚠️ Error cargando modelo LLM: {e}")
        print("   El sistema funcionará con respuestas basadas en reglas")
    
    yield
    # Shutdown (si es necesario limpiar recursos)
    print("🔌 Apagando servidor...")

# Aplicar lifespan al app
app.router.lifespan_context = lifespan

