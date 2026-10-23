"""API Route modules."""
from app.api.routes.health import router as health_router
from app.api.routes.skills import router as skills_router
from app.api.routes.matches import router as matches_router
from app.api.routes.gaps import router as gaps_router

__all__ = ["health_router", "skills_router", "matches_router", "gaps_router"]
