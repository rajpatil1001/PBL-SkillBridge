"""Application configuration loaded from environment variables using Pydantic Settings."""

import os
from pathlib import Path
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    SERVICE_NAME: str = "SkillBridge Skill Intelligence Service"
    SERVICE_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", description="Environment mode: development, staging, production")
    DEBUG: bool = False

    API_V1_PREFIX: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS settings: restrict to Express backend and trusted UI origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5000",
    ]

    # File paths
    TAXONOMY_PATH: str = str(BASE_DIR / "data" / "taxonomy.json")
    RESOURCES_PATH: str = str(BASE_DIR / "data" / "resources.json")

    # Evidence-Aware Scoring Defaults
    DEFAULT_RECENCY_HALF_LIFE_DAYS: int = 365
    DEFAULT_RECENCY_FLOOR: float = 0.25
    CORROBORATION_BONUS_PER_SOURCE: float = 0.08
    MAX_CORROBORATION_BONUS: float = 0.24

    # Logging & Privacy Settings
    LOG_LEVEL: str = "INFO"
    SANITIZE_LOG_PII: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)


settings = Settings()
