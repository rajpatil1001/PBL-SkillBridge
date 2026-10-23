"""Common models, enumerations, and schemas used across the Skill Intelligence Service."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SkillCategory(str, Enum):
    PROGRAMMING_LANGUAGE = "programming_language"
    FRAMEWORK = "framework"
    DATABASE = "database"
    CLOUD_DEVOPS = "cloud_devops"
    AI_ML = "ai_ml"
    DATA_ENGINEERING = "data_engineering"
    TESTING_QA = "testing_qa"
    WEB_TECHNOLOGY = "web_technology"
    SECURITY = "security"
    METHODOLOGY = "methodology"
    SOFT_SKILL = "soft_skill"
    TOOLS = "tools"
    OTHER = "other"


class EvidenceSourceType(str, Enum):
    VERIFIED_ASSESSMENT = "verified_assessment"
    COURSE_CERTIFICATE = "course_certificate"
    CAPSTONE_PROJECT = "capstone_project"
    GITHUB_REPOSITORY = "github_repository"
    RESUME_MENTION = "resume_mention"
    INTERVIEW_EVALUATION = "interview_evaluation"
    PEER_REVIEW = "peer_review"
    SELF_REPORTED = "self_reported"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    PENDING_VERIFICATION = "pending_verification"
    UNVERIFIED = "unverified"
    REJECTED = "rejected"


class ProficiencyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class StandardErrorDetail(BaseModel):
    loc: Optional[List[str]] = Field(default=None, description="Location of the error (e.g. field path)")
    msg: str = Field(..., description="Human-readable error description")
    type: str = Field(..., description="Error type identifier")


class ErrorResponse(BaseModel):
    error: str = Field(..., description="High-level error code or summary")
    message: str = Field(..., description="Clear explanatory message")
    details: Optional[List[StandardErrorDetail]] = Field(default=None, description="Detailed validation or sub-errors")
    status_code: int = Field(..., description="HTTP status code")
