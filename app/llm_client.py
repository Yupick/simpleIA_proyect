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
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from app.core.settings import settings

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

def decode_token_from_cookie(request: Request):
    """Decodifica el token JWT de la cookie y retorna la info del usuario."""
    token = request.cookies.get("access_token")
    if not token:
        print(f"DEBUG: No token found in cookies. Available cookies: {list(request.cookies.keys())}")
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username = payload.get("sub")
        is_admin = payload.get("is_admin", False)
        if username:
            print(f"DEBUG: Token decoded successfully. User: {username}, is_admin: {is_admin}")
            return {"username": username, "is_admin": is_admin}
    except Exception as e:
        print(f"DEBUG: Error decoding token: {e}")
        pass
    return None

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
    payload = {"username": username, "password": password}
    try:
        response = requests.post(f"{API_URL}/auth/login", data=payload)
        response.raise_for_status()
        data = response.json()
        access_token = data.get("access_token")
        is_admin = data.get("is_admin", False)
        if not access_token:
            return HTMLResponse("Error: No token obtained", status_code=400)
        
        # Redirigir a /admin si es admin, sino a /
        redirect_url = "/admin" if is_admin else "/"
        redirect = RedirectResponse(url=redirect_url, status_code=302)
        secure = os.getenv("ENVIRONMENT", "development") == "production"
        redirect.set_cookie(key="access_token", value=access_token, httponly=True, secure=secure, samesite="lax")
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
    """Dashboard principal admin."""
    user = decode_token_from_cookie(request)
    if not user or not user.get("is_admin"):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "user": user,
        "active_tab": "dashboard"
    })


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


@app.api_route("/api/admin/providers/current", methods=["GET"], response_class=JSONResponse)
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


@app.api_route("/api/admin/providers/switch", methods=["POST"], response_class=JSONResponse)
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
