"""Skill Gap Analysis and Learning Path Recommendation endpoints."""

from fastapi import APIRouter, HTTPException, status
from app.models.gap import AnalyzeGapsRequest, AnalyzeGapsResponse
from app.services.recommender import recommender_service
from app.utils.logging import logger

router = APIRouter(prefix="/gaps", tags=["Skill Gap Analysis & Recommendations"])


@router.post(
    "/analyze",
    response_model=AnalyzeGapsResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Student Skill Gaps and Recommend Learning Paths",
    response_description="Identified deficits, readiness score, prioritized study plan, and sample resources",
)
def analyze_skill_gaps(request: AnalyzeGapsRequest) -> AnalyzeGapsResponse:
    """Computes deficits between a student's current evidenced skills and target competency benchmarks.

    - Generates personalized learning recommendations mapped from a configurable catalogue.
    - Accurately labels seeded catalogue materials as sample resources.
    - Returns calculated readiness percentage, critical gap indicators, and estimated study hours.
    """
    try:
        logger.info(
            f"Gap analysis request received: student_id='{request.student_id}', "
            f"target_role='{request.target_role_title}', target_skills_count={len(request.target_skills)}"
        )
        return recommender_service.analyze(request)
    except Exception as exc:
        logger.error(f"Error analyzing skill gaps: {str(exc)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal gap analysis failure: {str(exc)}"
        )
