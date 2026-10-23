"""Candidate-Role Matching and Multi-Candidate Ranking endpoints."""

from fastapi import APIRouter, HTTPException, status
from app.models.match import RankMatchesRequest, RankMatchesResponse
from app.services.matcher import matcher_service
from app.utils.logging import logger

router = APIRouter(prefix="/matches", tags=["Role Matching & Ranking"])


@router.post(
    "/rank",
    response_model=RankMatchesResponse,
    status_code=status.HTTP_200_OK,
    summary="Rank Candidates for a Specified Role",
    response_description="Ranked candidate list with match scores, strengths, deficits, and explainability",
)
def rank_candidates_for_role(request: RankMatchesRequest) -> RankMatchesResponse:
    """Evaluates candidate skill portfolios against job/role specifications and deterministically ranks them.

    - Matches each required skill against candidate's evidenced proficiency and confidence.
    - Categorizes skills into **Matched**, **Weak**, and **Missing**.
    - Evaluates critical skill bottlenecks.
    - Yields human-readable rationale and an audit explainability field.
    - Strictly non-discriminatory: personal and protected attributes are neither accepted nor evaluated.
    """
    try:
        logger.info(
            f"Matching request received: role_id='{request.role.role_id}', "
            f"role_title='{request.role.role_title}', total_candidates={len(request.candidates)}"
        )
        return matcher_service.rank(request)
    except Exception as exc:
        logger.error(f"Error computing candidate rankings: {str(exc)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal ranking computation failure: {str(exc)}"
        )
