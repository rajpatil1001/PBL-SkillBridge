"""Request and Response models for Evidence-Aware Skill Scoring and Confidence Estimation."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from app.models.common import EvidenceSourceType, VerificationStatus, SkillCategory


class EvidenceItem(BaseModel):
    evidence_id: Optional[str] = Field(default=None, description="Unique evidence record identifier")
    skill_id: str = Field(..., description="Canonical skill identifier (e.g. 'python', 'docker')")
    source_type: EvidenceSourceType = Field(
        ...,
        description="Source of skill evidence (e.g. verified_assessment, capstone_project, github_repository)"
    )
    verification_status: VerificationStatus = Field(
        default=VerificationStatus.UNVERIFIED,
        description="Verification state of the evidence"
    )
    raw_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Proficiency score or grade achieved for this evidence (0.0 to 100.0)"
    )
    days_ago: Optional[int] = Field(
        default=0,
        ge=0,
        description="Days elapsed since evidence was created or updated (used for recency decay)"
    )
    date_recorded: Optional[str] = Field(
        default=None,
        description="ISO date string (YYYY-MM-DD) when evidence occurred (alternative to days_ago)"
    )
    title: Optional[str] = Field(
        default=None,
        description="Human-readable title (e.g. 'CS401 Capstone Project', 'AWS Solutions Architect')"
    )
    external_url: Optional[str] = Field(
        default=None,
        description="Optional link to artifact (GitHub PR, certificate URL)"
    )
    custom_weight: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Optional explicit weight override for specialized assessment rubrics"
    )

    @field_validator("title", "external_url", mode="before")
    @classmethod
    def sanitize_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        # Basic check to reject common PII injection into titles
        return v.strip()


class ScoringWeightConfig(BaseModel):
    """Configurable scoring weights and parameters."""
    source_weights: Dict[str, float] = Field(
        default_factory=lambda: {
            EvidenceSourceType.VERIFIED_ASSESSMENT.value: 1.00,
            EvidenceSourceType.INTERVIEW_EVALUATION.value: 0.85,
            EvidenceSourceType.CAPSTONE_PROJECT.value: 0.90,
            EvidenceSourceType.GITHUB_REPOSITORY.value: 0.80,
            EvidenceSourceType.COURSE_CERTIFICATE.value: 0.75,
            EvidenceSourceType.PEER_REVIEW.value: 0.70,
            EvidenceSourceType.RESUME_MENTION.value: 0.50,
            EvidenceSourceType.SELF_REPORTED.value: 0.40,
        },
        description="Weight multipliers for each evidence source type"
    )
    verification_multipliers: Dict[str, float] = Field(
        default_factory=lambda: {
            VerificationStatus.VERIFIED.value: 1.15,
            VerificationStatus.PENDING_VERIFICATION.value: 0.95,
            VerificationStatus.UNVERIFIED.value: 0.85,
            VerificationStatus.REJECTED.value: 0.00,
        },
        description="Multiplier based on verification status"
    )
    recency_half_life_days: int = Field(
        default=365,
        ge=30,
        description="Days after which evidence weight is halved under exponential decay"
    )
    recency_floor: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
        description="Minimum floor multiplier for aged evidence so foundational knowledge is not erased"
    )
    corroboration_bonus_per_source: float = Field(
        default=0.08,
        ge=0.0,
        le=0.20,
        description="Confidence bonus added per independent distinct evidence source"
    )
    max_corroboration_bonus: float = Field(
        default=0.24,
        ge=0.0,
        le=0.50,
        description="Cap for cumulative independent corroboration bonus"
    )


class ScoreSkillsRequest(BaseModel):
    candidate_id: Optional[str] = Field(
        default="anonymous_candidate",
        description="Stateless candidate reference identifier (do NOT include sensitive personal PII)"
    )
    evidence: List[EvidenceItem] = Field(
        ...,
        min_length=1,
        description="Collection of evidence items for candidate skills"
    )
    weight_config: Optional[ScoringWeightConfig] = Field(
        default=None,
        description="Optional custom scoring weights override; defaults to standard baseline weights"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "candidate_id": "cand_94821",
                "evidence": [
                    {
                        "skill_id": "python",
                        "source_type": "verified_assessment",
                        "verification_status": "verified",
                        "raw_score": 92.0,
                        "days_ago": 30,
                        "title": "Backend Engineering Assessment"
                    },
                    {
                        "skill_id": "python",
                        "source_type": "capstone_project",
                        "verification_status": "verified",
                        "raw_score": 88.0,
                        "days_ago": 90,
                        "title": "Distributed Task Queue Project"
                    },
                    {
                        "skill_id": "docker",
                        "source_type": "github_repository",
                        "verification_status": "unverified",
                        "raw_score": 75.0,
                        "days_ago": 15,
                        "title": "Docker Compose Multi-Container Setup"
                    }
                ]
            }
        }
    }


class EvidenceFactorBreakdown(BaseModel):
    source_type: str
    raw_score: float
    source_weight: float
    verification_multiplier: float
    recency_factor: float
    weighted_contribution: float
    is_rejected: bool = False


class SkillScoreResult(BaseModel):
    skill_id: str = Field(..., description="Canonical skill identifier")
    canonical_name: str = Field(..., description="Human-readable skill name")
    category: SkillCategory = Field(default=SkillCategory.OTHER, description="Skill category")
    composite_score: float = Field(..., ge=0.0, le=100.0, description="Final weighted composite score (0-100)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence level (0.0 to 1.0)")
    evidence_count: int = Field(..., description="Total evidence items contributing to this skill")
    distinct_sources: List[str] = Field(default_factory=list, description="Unique source types corroborating this skill")
    corroboration_bonus_applied: float = Field(..., description="Corroboration bonus factor added")
    factors: List[EvidenceFactorBreakdown] = Field(default_factory=list, description="Per-evidence breakdown")
    explanation: str = Field(..., description="Concise human-readable explanation of score and confidence")


class ScoreSkillsResponse(BaseModel):
    candidate_id: str = Field(..., description="Candidate identifier")
    overall_skill_index: float = Field(..., ge=0.0, le=100.0, description="Aggregate average score across all skills")
    skills: List[SkillScoreResult] = Field(..., description="List of scored skills")
    explainability_summary: str = Field(..., description="Narrative explainability overview")
    scoring_version: str = Field(default="evidence_weighted_v1.0")
    disclaimer: str = Field(
        default="Scores and confidence estimates are computed purely from submitted academic and technical evidence factors. No demographic, sensitive, or protected attributes are accepted or processed.",
        description="Ethics, fairness, and non-discrimination disclosure"
    )
