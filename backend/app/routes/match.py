import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.schemas.auth import CurrentUser
from app.schemas.match import MatchRequest, MatchResponse
from app.services.firebase_auth import get_current_user
from app.services.resume_matcher import calculate_resume_match

router = APIRouter(prefix="/api/match", tags=["Match"])
logger = logging.getLogger(__name__)


@router.post("/analyze", response_model=MatchResponse)
async def analyze_match(
    request: MatchRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> MatchResponse:
    logger.info("Legacy deterministic resume match requested.")
    try:
        analysis = await run_in_threadpool(
            calculate_resume_match,
            request.resume,
            request.job,
        )
    except Exception as exc:
        logger.exception("Unexpected deterministic resume match failure.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to calculate the resume match right now.",
        ) from exc

    logger.info("Legacy deterministic resume match completed.")
    return MatchResponse(
        resume_id=request.resume_id,
        job_id=request.job_id,
        status="matched",
        match=analysis,
    )
