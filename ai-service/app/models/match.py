"""Request and Response models for Role Matching and Multi-Candidate Ranking."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SkillImportance(str, Enum):
    CRITICAL = "critical"        # Must-have (e.g. 1.5x weight)
    IMPORTANT = "important"      # Core requirement (1.0x weight)
    NICE_TO_HAVE = "nice_to_have"# Bonus skill (0.5x weight)


class SkillMatchStatus(str, Enum):
    MATCHED = "matched"
    WEAK = "weak"
    MISSING = "missing"


class RequiredSkillSpec(BaseModel):
    skill_id: str = Field(..., description="Canonical skill identifier (e.g. 'python', 'sql')")
    minimum_score: float = Field(default=60.0, ge=0.0, le=100.0, description="Minimum benchmark score (0-100)")
    importance: SkillImportance = Field(default=SkillImportance.IMPORTANT, description="Criticality of the skill for the role")
    weight: Optional[float] = Field(default=None, ge=0.1, le=5.0, description="Explicit numerical weight override")


class RoleRequirement(BaseModel):
    role_id: str = Field(..., description="Role or job opening unique identifier")
    role_title: str = Field(..., description="Display title (e.g. 'Junior Backend Engineer')")
    department: Optional[str] = Field(default=None, description="Department or team")
    required_skills: List[RequiredSkillSpec] = Field(..., min_length=1, description="List of required skill specifications")
    minimum_overall_threshold: float = Field(default=50.0, ge=0.0, le=100.0, description="Minimum acceptable match score")


class CandidateSkillEvidence(BaseModel):
    skill_id: str = Field(..., description="Canonical skill identifier")
    score: float = Field(..., ge=0.0, le=100.0, description="Candidate proficiency score (0-100)")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in the score estimation")


class CandidateProfile(BaseModel):
    candidate_id: str = Field(..., description="Stateless candidate reference identifier")
    skills: List[CandidateSkillEvidence] = Field(..., min_length=1, description="Candidate's evidenced skills")


class SkillMatchEvaluation(BaseModel):
    skill_id: str
    canonical_name: str
    status: SkillMatchStatus
    importance: SkillImportance
    required_score: float
    candidate_score: float
    candidate_confidence: float
    impact_score: float = Field(..., description="Relative contribution to overall role match score")
    note: str


class MatchResult(BaseModel):
    candidate_id: str = Field(..., description="Candidate reference identifier")
    rank: Optional[int] = Field(default=None, description="Assigned position in ranking")
    match_score: float = Field(..., ge=0.0, le=100.0, description="Composite role match score (0-100)")
    fit_level: str = Field(..., description="Categorical fit rating ('Strong Fit', 'Moderate Fit', 'Potential with Gaps', 'Low Fit')")
    matched_skills: List[SkillMatchEvaluation] = Field(default_factory=list, description="Skills meeting or exceeding threshold")
    weak_skills: List[SkillMatchEvaluation] = Field(default_factory=list, description="Skills present but below target proficiency")
    missing_skills: List[SkillMatchEvaluation] = Field(default_factory=list, description="Required skills with zero evidence")
    strengths: List[str] = Field(default_factory=list, description="Key candidate strengths for this role")
    reasons: List[str] = Field(default_factory=list, description="Concise human-readable rationale")
    explainability: str = Field(..., description="Transparent audit summary of how match score was determined")


class RankMatchesRequest(BaseModel):
    role: RoleRequirement = Field(..., description="Role requirements specification")
    candidates: List[CandidateProfile] = Field(..., min_length=1, description="List of candidate skill profiles to rank")
    top_k: Optional[int] = Field(default=None, ge=1, description="Optionally limit result to top K candidates")

    model_config = {
        "json_schema_extra": {
            "example": {
                "role": {
                    "role_id": "role_backend_jr",
                    "role_title": "Junior Python Backend Developer",
                    "required_skills": [
                        {"skill_id": "python", "minimum_score": 70.0, "importance": "critical"},
                        {"skill_id": "fastapi", "minimum_score": 60.0, "importance": "important"},
                        {"skill_id": "postgresql", "minimum_score": 60.0, "importance": "important"},
                        {"skill_id": "docker", "minimum_score": 50.0, "importance": "nice_to_have"}
                    ]
                },
                "candidates": [
                    {
                        "candidate_id": "cand_alice",
                        "skills": [
                            {"skill_id": "python", "score": 88.0, "confidence": 0.95},
                            {"skill_id": "fastapi", "score": 80.0, "confidence": 0.85},
                            {"skill_id": "postgresql", "score": 75.0, "confidence": 0.80},
                            {"skill_id": "docker", "score": 65.0, "confidence": 0.70}
                        ]
                    },
                    {
                        "candidate_id": "cand_bob",
                        "skills": [
                            {"skill_id": "python", "score": 65.0, "confidence": 0.70},
                            {"skill_id": "fastapi", "score": 45.0, "confidence": 0.60}
                        ]
                    }
                ]
            }
        }
    }


class RankMatchesResponse(BaseModel):
    role_id: str
    role_title: str
    total_candidates_evaluated: int
    rankings: List[MatchResult]
    explainability_notes: str
    fairness_statement: str = Field(
        default="Ranking is computed solely through mathematical evaluation of demonstrated skill proficiencies against documented role specifications. Personal identities and protected attributes are neither solicited nor evaluated.",
        description="Non-discrimination and ethical AI guarantee"
    )
