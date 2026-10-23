"""Request and Response models for Skill Gap Analysis and Learning Recommendations."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GapUrgency(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ResourceType(str, Enum):
    COURSE = "course"
    PROJECT_TUTORIAL = "project_tutorial"
    HANDS_ON_LAB = "hands_on_lab"
    DOCUMENTATION = "documentation"
    INTERACTIVE_SANDBOX = "interactive_sandbox"
    BOOK = "book"


class LearningResource(BaseModel):
    resource_id: str = Field(..., description="Unique resource identifier")
    title: str = Field(..., description="Title of course, lab, or documentation")
    provider: str = Field(..., description="Educational provider or platform")
    resource_type: ResourceType = Field(..., description="Format of the learning material")
    difficulty: str = Field(..., description="Target proficiency: 'beginner', 'intermediate', or 'advanced'")
    estimated_hours: float = Field(..., ge=0.5, description="Estimated time investment in hours")
    url: Optional[str] = Field(default=None, description="Direct URL to resource")
    is_sample: bool = Field(
        default=True,
        description="Explicit label indicating whether this is a seeded reference resource or live LMS sync"
    )
    description: Optional[str] = Field(default=None, description="Brief synopsis of what this resource covers")


class TargetSkillDemand(BaseModel):
    skill_id: str = Field(..., description="Canonical skill identifier")
    target_score: float = Field(default=70.0, ge=0.0, le=100.0, description="Target proficiency benchmark")
    priority: GapUrgency = Field(default=GapUrgency.HIGH, description="Priority level of this skill requirement")


class CurrentSkillStatus(BaseModel):
    skill_id: str = Field(..., description="Canonical skill identifier")
    current_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Current evidenced score (0-100)")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in current measurement")


class SkillGapItem(BaseModel):
    skill_id: str = Field(..., description="Canonical skill identifier")
    canonical_name: str = Field(..., description="Canonical skill display name")
    current_score: float = Field(..., description="Current evaluated proficiency")
    target_score: float = Field(..., description="Goal proficiency benchmark")
    gap_delta: float = Field(..., description="Point deficit needed to meet requirement (target - current)")
    urgency: GapUrgency = Field(..., description="Urgency of closing this gap")
    recommended_action: str = Field(..., description="Actionable advice for the learner")
    recommended_resources: List[LearningResource] = Field(
        default_factory=list,
        description="Curated learning items labeled with sample status"
    )


class AnalyzeGapsRequest(BaseModel):
    student_id: Optional[str] = Field(
        default="anonymous_student",
        description="Stateless learner reference (do not pass personal demographic data)"
    )
    target_role_title: Optional[str] = Field(
        default=None,
        description="Target job or role aspiration (e.g. 'Cloud DevOps Engineer')"
    )
    target_skills: List[TargetSkillDemand] = Field(
        ...,
        min_length=1,
        description="List of target skill goals and required proficiencies"
    )
    current_skills: List[CurrentSkillStatus] = Field(
        default_factory=list,
        description="Current skill proficiencies from evidence evaluation (may be empty for complete beginner)"
    )
    max_recommendations_per_skill: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum suggested learning resources per identified gap"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "student_id": "stud_102",
                "target_role_title": "Full Stack Engineer",
                "target_skills": [
                    {"skill_id": "python", "target_score": 75.0, "priority": "high"},
                    {"skill_id": "react", "target_score": 70.0, "priority": "high"},
                    {"skill_id": "docker", "target_score": 60.0, "priority": "medium"},
                    {"skill_id": "postgresql", "target_score": 65.0, "priority": "medium"}
                ],
                "current_skills": [
                    {"skill_id": "python", "current_score": 80.0, "confidence": 0.9},
                    {"skill_id": "react", "current_score": 40.0, "confidence": 0.75}
                ],
                "max_recommendations_per_skill": 2
            }
        }
    }


class AnalyzeGapsResponse(BaseModel):
    student_id: str
    target_role_title: Optional[str]
    total_gaps_identified: int
    critical_gaps_count: int
    readiness_percentage: float = Field(..., ge=0.0, le=100.0, description="Overall skill readiness score (0-100%)")
    gaps: List[SkillGapItem] = Field(default_factory=list, description="Ordered list of skill gaps from most critical")
    total_estimated_learning_hours: float = Field(..., description="Estimated aggregate study time to bridge all gaps")
    priority_action_plan: List[str] = Field(default_factory=list, description="Step-by-step roadmap suggestions")
    explainability: str = Field(..., description="Audit rationale explaining how gaps and priorities were calculated")
    sample_resources_disclaimer: str = Field(
        default="Recommended resources are seeded catalogue samples for demonstration and foundational learning paths.",
        description="Catalog attribution and sample notice"
    )
