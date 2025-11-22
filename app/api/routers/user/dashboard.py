"""
Dashboard Router - Panel principal de usuario.
Ruta: /user/*
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from app.security.auth import get_current_user

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(prefix="/user", tags=["User Dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request, user: dict = Depends(get_current_user)):
    """
    Dashboard principal del usuario.
    Muestra resumen de productos, agenda, tareas, y acceso a asistentes.
    """
    # Verificar que no sea super admin
    if user.get("role") == "superadmin":
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    
    return templates.TemplateResponse("user/dashboard.html", {
        "request": request,
        "user": user
    })


@router.get("", response_class=HTMLResponse)
async def user_root(request: Request, user: dict = Depends(get_current_user)):
    """Redirige /user a /user/dashboard."""
    return RedirectResponse(url="/user/dashboard", status_code=302)
