"""Route handlers for API endpoints."""

from app.routes.auth_routes import router as auth_router
from app.routes.cleanup_routes import router as cleanup_router
from app.routes.entry_routes import router as entry_router
from app.routes.page_routes import router as page_router

__all__ = [
    "auth_router",
    "cleanup_router",
    "entry_router",
    "page_router",
]
