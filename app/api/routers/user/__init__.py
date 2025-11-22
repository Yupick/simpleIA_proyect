"""
User routers - Endpoints para panel de usuario (no super admins).
Todos los datos están aislados por user_id.
"""

from .dashboard import router as dashboard_router

__all__ = ["dashboard_router"]
