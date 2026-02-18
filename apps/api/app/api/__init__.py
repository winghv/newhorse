"""
API routers module
"""
from .projects import router as projects_router
from .chat import router as chat_router
from .agents import router as agents_router
from .files import router as files_router
from .preview import router as preview_router
from .activity import router as activity_router
from .skills import router as skills_router

__all__ = ["projects_router", "chat_router", "agents_router", "files_router", "preview_router", "activity_router", "skills_router"]
