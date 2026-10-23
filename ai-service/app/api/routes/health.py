"""Health check and service status endpoint."""

from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter
from app.config import settings
from app.services.extractor import extractor_service
from app.services.recommender import recommender_service

router = APIRouter(tags=["Health & Status"])

START_TIME = datetime.now(timezone.utc)


@router.get(
    "/health",
    summary="Service Health Check",
    response_description="Status and telemetry of the AI/ML Skill Intelligence service",
)
def get_health() -> Dict[str, Any]:
    """Returns runtime health status, version telemetry, and active taxonomy statistics."""
    uptime_seconds = round((datetime.now(timezone.utc) - START_TIME).total_seconds(), 1)
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": uptime_seconds,
        "active_taxonomy_skills": len(extractor_service.taxonomy),
        "active_resource_catalogue_skills": len(recommender_service.catalogue),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
