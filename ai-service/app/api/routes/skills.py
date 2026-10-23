"""Skill Intelligence endpoints: extraction and evidence-aware scoring."""

from fastapi import APIRouter, HTTPException, status
from app.models.extract import ExtractSkillsRequest, ExtractSkillsResponse
from app.models.score import ScoreSkillsRequest, ScoreSkillsResponse
from app.services.extractor import extractor_service
from app.services.scorer import scorer_service
from app.utils.logging import logger

router = APIRouter(prefix="/skills", tags=["Skill Extraction & Scoring"])


@router.post(
    "/extract",
    response_model=ExtractSkillsResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract Skills from Document Text",
    response_description="Canonical skills detected with character offsets and confidence metrics",
)
def extract_skills(request: ExtractSkillsRequest) -> ExtractSkillsResponse:
    """Extracts technical and domain competencies from resumes, project summaries, or job descriptions.

    - **text**: Raw text body (3 to 150,000 characters).
    - **document_type**: Document classification ('resume', 'project', 'job_description', 'general').
    - **confidence_threshold**: Minimum threshold (0.0 - 1.0) for returning identified skills.
    - **include_context**: When True, attaches surrounding sentence windows and section headers.
    """
    try:
        logger.info(
            f"Extraction request received: doc_type='{request.document_type}', "
            f"length={len(request.text)} chars, threshold={request.confidence_threshold}"
        )
        return extractor_service.extract(request)
    except Exception as exc:
        logger.error(f"Error executing skill extraction: {str(exc)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal extraction pipeline failure: {str(exc)}"
        )


@router.post(
    "/score",
    response_model=ScoreSkillsResponse,
    status_code=status.HTTP_200_OK,
    summary="Evidence-Aware Skill Scoring & Confidence Estimation",
    response_description="Weighted skill scores, confidence levels, and explainability breakdown",
)
def score_skills(request: ScoreSkillsRequest) -> ScoreSkillsResponse:
    """Calculates weighted skill proficiencies and confidence estimates from academic/technical evidence.

    Accounts for:
    - **Evidence Source**: Verified assessments (1.0x), Capstone projects (0.9x), GitHub repos (0.8x), etc.
    - **Verification Multiplier**: Verified audits boost confidence; rejected records are disqualified.
    - **Recency Decay**: Exponential half-life decay discounts stale evidence.
    - **Multi-Source Corroboration**: Boosts confidence when multiple independent sources corroborate a skill.
    """
    try:
        logger.info(
            f"Scoring request received: candidate_id='{request.candidate_id}', "
            f"total_evidence_items={len(request.evidence)}"
        )
        return scorer_service.score(request)
    except Exception as exc:
        logger.error(f"Error computing evidence-aware scores: {str(exc)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal scoring failure: {str(exc)}"
        )
