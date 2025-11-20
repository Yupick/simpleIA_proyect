"""
Router para el panel de administración.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from ..security.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="templates")

@router.get("", response_class=HTMLResponse)
async def admin_dashboard(request: Request, current_user=Depends(get_current_user)):
    """
    Panel de administración con métricas visuales.
    Requiere autenticación.
    """
    return templates.TemplateResponse("admin.html", {"request": request, "user": current_user})
