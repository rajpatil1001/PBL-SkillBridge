"""Request and Response models for the Skill Extraction endpoint."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.models.common import SkillCategory


class ExtractSkillsRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=3,
        max_length=150000,
        description="Raw document text (e.g. resume, project description, course syllabus, or job posting)."
    )
    document_type: str = Field(
        default="resume",
        description="Type of document analyzed: 'resume', 'project', 'job_description', 'syllabus', or 'general'."
    )
    confidence_threshold: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold (0.0 to 1.0) to include a detected skill in results."
    )
    include_context: bool = Field(
        default=True,
        description="Whether to include surrounding contextual snippets and detected section headers."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "Experienced Full Stack Developer skilled in Python, FastAPI, React, and PostgreSQL. Built scalable microservices deployed on AWS with Docker.",
                "document_type": "resume",
                "confidence_threshold": 0.5,
                "include_context": True
            }
        }
    }


class ExtractedSkillItem(BaseModel):
    skill_id: str = Field(..., description="Normalized canonical skill identifier (slug format)")
    canonical_name: str = Field(..., description="Canonical human-readable display name")
    category: SkillCategory = Field(..., description="Classification category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score")
    matched_text: str = Field(..., description="Exact token / alias string matched in the text")
    start_char: int = Field(..., ge=0, description="Character start offset index")
    end_char: int = Field(..., ge=0, description="Character end offset index")
    context_snippet: Optional[str] = Field(default=None, description="Surrounding sentence or phrase window")
    section_header: Optional[str] = Field(default=None, description="Detected resume/document section if available")


class ExtractionMetadata(BaseModel):
    pipeline: str = Field(default="rule_taxonomy_baseline_v1", description="Identifier of the extraction pipeline")
    version: str = Field(default="1.0.0", description="Pipeline semantic version")
    execution_time_ms: float = Field(..., description="Elapsed processing time in milliseconds")
    methodology: str = Field(
        default="Aho-Corasick / regex token boundary matching over canonical taxonomy with contextual alias disambiguation.",
        description="Description of the extraction method used"
    )
    limitations: str = Field(
        default="Baseline heuristic and taxonomy matching. Does not perform deep dependency parsing or generative hallucination. Only skills present in or mapped to the canonical taxonomy are extracted.",
        description="Known technical limitations"
    )


class ExtractSkillsResponse(BaseModel):
    skills: List[ExtractedSkillItem] = Field(default_factory=list, description="List of uniquely extracted skills")
    total_detected: int = Field(..., description="Count of extracted skills meeting threshold")
    document_type: str = Field(..., description="Document type provided in request")
    metadata: ExtractionMetadata = Field(..., description="Pipeline execution metadata and transparency disclosure")
