import logging
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pymongo.errors import DuplicateKeyError, PyMongoError
from starlette.concurrency import run_in_threadpool

from app.dependencies.persistence import get_persisted_user, require_database
from app.repositories.jobs import create_job, delete_job_record, get_job_by_id, list_user_jobs, update_match
from app.repositories.optimizations import delete_for_job, list_for_job
from app.repositories.resumes import get_resume_by_id
from app.schemas.auth import CurrentUser
from app.schemas.job import JobAnalysisRequest, JobAnalysisResponse, JobDetailResponse, JobListResponse
from app.schemas.match import MatchResponse
from app.schemas.resume import ResumeSchema
from app.schemas.job import JobAnalysisSchema
from app.services.mistral_service import MistralConfigurationError, MistralResponseError, MistralServiceError, analyze_job_description
from app.services.resume_matcher import calculate_resume_match
from app.services.s3_service import S3ConfigurationError, S3OperationError, delete_file

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])
logger = logging.getLogger(__name__)


def _canonical_id(value: str, label: str = "job") -> str:
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError) as exc:
        raise HTTPException(status_code=422, detail=f"Invalid {label} ID.") from exc
    canonical = str(parsed)
    if canonical != value.lower():
        raise HTTPException(status_code=422, detail=f"Invalid {label} ID.")
    return canonical


def _database_unavailable(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail="Database is temporarily unavailable. Please try again.")


@router.post("/analyze", response_model=JobAnalysisResponse)
async def analyze_job(request: JobAnalysisRequest, current_user: Annotated[CurrentUser, Depends(get_persisted_user)], database: Annotated[Any, Depends(require_database)]) -> JobAnalysisResponse:
    try:
        resume = await get_resume_by_id(database, current_user.uid, request.resume_id)
    except PyMongoError as exc:
        raise _database_unavailable(exc) from exc
    if not resume or resume.get("status") != "parsed" or not resume.get("parsed_resume"):
        raise HTTPException(status_code=404, detail="A parsed resume was not found.")
    try:
        analysis = await run_in_threadpool(analyze_job_description, request.company, request.role, request.job_description)
    except MistralConfigurationError as exc:
        raise HTTPException(status_code=503, detail="Job analysis service is not configured.") from exc
    except (MistralResponseError, MistralServiceError) as exc:
        raise HTTPException(status_code=502, detail="Unable to analyze this job right now. Please try again.") from exc
    job_id = str(uuid4())
    try:
        await create_job(database, {
            "job_id": job_id, "user_id": current_user.uid, "resume_id": request.resume_id,
            "company": request.company, "role": request.role, "job_description": request.job_description,
            "analysis": analysis.model_dump(), "match_analysis": None, "status": "analyzed",
        })
    except (DuplicateKeyError, PyMongoError) as exc:
        raise _database_unavailable(exc) from exc
    return JobAnalysisResponse(job_id=job_id, resume_id=request.resume_id, status="analyzed", analysis=analysis)


@router.get("", response_model=JobListResponse)
async def list_jobs(current_user: Annotated[CurrentUser, Depends(get_persisted_user)], database: Annotated[Any, Depends(require_database)], resume_id: Annotated[str | None, Query()] = None) -> JobListResponse:
    canonical_resume_id = _canonical_id(resume_id, "resume") if resume_id else None
    try:
        documents = await list_user_jobs(database, current_user.uid, resume_id=canonical_resume_id)
    except PyMongoError as exc:
        raise _database_unavailable(exc) from exc
    return JobListResponse(items=documents)


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job(job_id: str, current_user: Annotated[CurrentUser, Depends(get_persisted_user)], database: Annotated[Any, Depends(require_database)]) -> JobDetailResponse:
    canonical_id = _canonical_id(job_id)
    try:
        document = await get_job_by_id(database, current_user.uid, canonical_id)
    except PyMongoError as exc:
        raise _database_unavailable(exc) from exc
    if not document:
        raise HTTPException(status_code=404, detail="Job was not found.")
    document.pop("_id", None)
    document.pop("user_id", None)
    return JobDetailResponse.model_validate(document)


@router.post("/{job_id}/match", response_model=MatchResponse)
async def match_job(job_id: str, current_user: Annotated[CurrentUser, Depends(get_persisted_user)], database: Annotated[Any, Depends(require_database)]) -> MatchResponse:
    canonical_id = _canonical_id(job_id)
    try:
        job = await get_job_by_id(database, current_user.uid, canonical_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job was not found.")
        resume = await get_resume_by_id(database, current_user.uid, job["resume_id"])
    except PyMongoError as exc:
        raise _database_unavailable(exc) from exc
    if not resume or not resume.get("parsed_resume"):
        raise HTTPException(status_code=404, detail="Parsed resume was not found.")
    try:
        analysis = await run_in_threadpool(
            calculate_resume_match,
            ResumeSchema.model_validate(resume["parsed_resume"]),
            JobAnalysisSchema.model_validate(job["analysis"]),
        )
        await update_match(database, current_user.uid, canonical_id, analysis.model_dump())
    except PyMongoError as exc:
        raise _database_unavailable(exc) from exc
    except Exception as exc:
        logger.exception("Unexpected deterministic resume match failure.")
        raise HTTPException(status_code=500, detail="Unable to calculate the resume match right now.") from exc
    return MatchResponse(resume_id=job["resume_id"], job_id=canonical_id, status="matched", match=analysis)


@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: str, current_user: Annotated[CurrentUser, Depends(get_persisted_user)], database: Annotated[Any, Depends(require_database)]) -> Response:
    canonical_id = _canonical_id(job_id)
    try:
        job = await get_job_by_id(database, current_user.uid, canonical_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job was not found.")
        optimizations = await list_for_job(database, current_user.uid, canonical_id)
        for item in optimizations:
            if item.get("generated_pdf"):
                try:
                    await run_in_threadpool(delete_file, item["generated_pdf"]["s3_key"])
                except (S3ConfigurationError, S3OperationError):
                    logger.exception("Generated PDF cleanup failed for job %s.", canonical_id)
        await delete_for_job(database, current_user.uid, canonical_id)
        await delete_job_record(database, current_user.uid, canonical_id)
    except PyMongoError as exc:
        raise _database_unavailable(exc) from exc
    return Response(status_code=204)
