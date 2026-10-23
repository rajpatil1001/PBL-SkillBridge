"""Convenience entry point for running the Skill Intelligence FastAPI server directly."""

import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"Starting {settings.SERVICE_NAME} on http://{settings.HOST}:{settings.PORT}")
    print(f"Swagger API Docs: http://{settings.HOST}:{settings.PORT}/docs")
    print(f"Health Check: http://{settings.HOST}:{settings.PORT}/health")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
