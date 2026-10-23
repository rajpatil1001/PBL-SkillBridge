"""Main FastAPI application entry point for SkillBridge Skill Intelligence Service."""

import time
from typing import Any, Dict
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import gaps_router, health_router, matches_router, skills_router
from app.config import settings
from app.models.common import ErrorResponse, StandardErrorDetail
from app.utils.logging import logger

app = FastAPI(
    title=settings.SERVICE_NAME,
    version=settings.SERVICE_VERSION,
    description=(
        "**SkillBridge AI/ML & Skill Intelligence Service (Person 3 Scope)**\n\n"
        "Provides stateless, high-performance microservice capabilities for:\n"
        "- **Skill Extraction**: High-precision taxonomy matching with contextual disambiguation.\n"
        "- **Evidence-Aware Scoring**: Multi-source weighting, verification audits, exponential recency decay, and independent corroboration.\n"
        "- **Role Matching & Multi-Candidate Ranking**: Deterministic, explainable matching with critical deficit handling.\n"
        "- **Skill Gap Analysis & Recommendations**: Gap delta calculation, study plans, and sample learning resources.\n\n"
        "*Designed for direct orchestration by the Express API.*"
    ),
    openapi_tags=[
        {"name": "Health & Status", "description": "Liveness, readiness, and runtime telemetry"},
        {"name": "Skill Extraction & Scoring", "description": "Text extraction and evidence-aware proficiency scoring"},
        {"name": "Role Matching & Ranking", "description": "Candidate portfolio matching against role criteria"},
        {"name": "Skill Gap Analysis & Recommendations", "description": "Deficit analysis and curated learning roadmaps"},
    ],
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Measures request execution time and adds X-Process-Time-Ms header."""
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = round((time.perf_counter() - start_time) * 1000.0, 2)
    response.headers["X-Process-Time-Ms"] = str(process_time)
    return response


# Standardized error response handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Translates Pydantic schema validation errors into standard ErrorResponse envelope."""
    details = [
        StandardErrorDetail(
            loc=[str(loc_item) for loc_item in err.get("loc", [])],
            msg=err.get("msg", "Validation error"),
            type=err.get("type", "value_error"),
        )
        for err in exc.errors()
    ]
    logger.warning(f"Request validation failure on {request.url.path}: {len(details)} invalid field(s).")
    payload = ErrorResponse(
        error="VALIDATION_ERROR",
        message="Incoming request payload failed schema validation.",
        details=details,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=payload.model_dump())


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Standardizes explicit HTTPExceptions."""
    payload = ErrorResponse(
        error="HTTP_ERROR",
        message=str(exc.detail),
        details=None,
        status_code=exc.status_code,
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catches unexpected exceptions, logs securely, and returns safe 500 error."""
    logger.error(f"Unhandled internal server error on {request.url.path}: {str(exc)}", exc_info=True)
    payload = ErrorResponse(
        error="INTERNAL_SERVER_ERROR",
        message="An unexpected internal service error occurred. Please try again or contact system support.",
        details=None,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload.model_dump())


# Mount routes
app.include_router(health_router)  # Mounted at /health
app.include_router(health_router, prefix=settings.API_V1_PREFIX)  # Also mounted at /api/v1/health
app.include_router(skills_router, prefix=settings.API_V1_PREFIX)
app.include_router(matches_router, prefix=settings.API_V1_PREFIX)
app.include_router(gaps_router, prefix=settings.API_V1_PREFIX)


@app.get("/", include_in_schema=False)
def root_redirect():
    """Root redirect / landing helper pointing to health and docs."""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.SERVICE_VERSION,
        "health": "/health",
        "docs": "/docs",
        "endpoints": [
            f"{settings.API_V1_PREFIX}/skills/extract",
            f"{settings.API_V1_PREFIX}/skills/score",
            f"{settings.API_V1_PREFIX}/matches/rank",
            f"{settings.API_V1_PREFIX}/gaps/analyze",
        ],
    }
