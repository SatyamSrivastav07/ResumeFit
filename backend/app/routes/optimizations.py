import logging
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pymongo.errors import DuplicateKeyError, PyMongoError
from starlette.concurrency import run_in_threadpool

from app.dependencies.persistence import get_persisted_user, require_database
from app.repositories.jobs import get_job_by_id, update_job_status
from app.repositories.optimizations import create_optimization, delete_optimization_record, get_optimization_by_id, public_optimization, update_applied_optimization, update_generated_pdf
from app.repositories.resumes import get_resume_by_id
from app.repositories.users import utc_now
from app.schemas.auth import CurrentUser
from app.schemas.job import JobAnalysisSchema
from app.schemas.match import MatchAnalysisSchema
from app.schemas.optimization import ApplyOptimizationResponse, ApplyPersistentOptimizationRequest, OptimizationDetailResponse, OptimizationResponse, OptimizationSuggestion, PersistentOptimizationRequest, ScoreComparison, validate_uuid_string
from app.schemas.pdf import PDFAccessResponse, PDFGenerationResponse
from app.schemas.resume import ResumeSchema
from app.services.mistral_service import MistralConfigurationError, MistralResponseError, MistralServiceError
from app.services.optimization_validator import UnsafeSuggestionsError, apply_approved_suggestions
from app.services.resume_optimizer import generate_resume_suggestions
from app.services.resume_renderer import ResumeRenderingError, generate_resume_pdf
from app.services.s3_service import S3ConfigurationError, S3OperationError, delete_file, generate_presigned_url, upload_file
from app.utils.filenames import build_resume_filename

router = APIRouter(prefix="/api/optimizations", tags=["Optimizations"])
logger = logging.getLogger(__name__)
PDF_URL_EXPIRES_IN = 900


def _validated_id(value: str) -> str:
    try:
        return validate_uuid_string(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="identifier must be a canonical UUID") from exc


def _database_unavailable(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail="Database is temporarily unavailable. Please try again.")


def _optimized_pdf_key(uid: str, resume_id: str, job_id: str, optimization_id: str) -> str:
    return f"users/{uid}/resumes/{resume_id}/jobs/{job_id}/optimizations/{optimization_id}/optimized.pdf"


def _create_pdf_access_urls(key: str, filename: str) -> tuple[str, str]:
    preview_url = generate_presigned_url(key, expires_in=PDF_URL_EXPIRES_IN, response_content_disposition="inline", response_content_type="application/pdf")
    download_url = generate_presigned_url(key, expires_in=PDF_URL_EXPIRES_IN, response_content_disposition=f'attachment; filename="{filename}"', response_content_type="application/pdf")
    return preview_url, download_url


@router.post("/generate", response_model=OptimizationResponse)
async def generate_optimizations(request: PersistentOptimizationRequest, current_user: Annotated[CurrentUser, Depends(get_persisted_user)], database: Annotated[Any, Depends(require_database)]) -> OptimizationResponse:
    try:
        job = await get_job_by_id(database, current_user.uid, request.job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job was not found.")
        resume = await get_resume_by_id(database, current_user.uid, job["resume_id"])
    except PyMongoError as exc:
        raise _database_unavailable(exc) from exc
    if not resume or not resume.get("parsed_resume") or not job.get("analysis") or not job.get("match_analysis"):
        raise HTTPException(status_code=409, detail="Complete resume matching before optimization.")
    resume_model = ResumeSchema.model_validate(resume["parsed_resume"])
    job_model = JobAnalysisSchema.model_validate(job["analysis"])
    match_model = MatchAnalysisSchema.model_validate(job["match_analysis"])
    try:
        suggestions = await run_in_threadpool(generate_resume_suggestions, resume_model, job_model, match_model)
    except MistralConfigurationError as exc:
        raise HTTPException(status_code=503, detail="Resume optimization service is not configured.") from exc
    except (MistralResponseError, MistralServiceError) as exc:
        raise HTTPException(status_code=502, detail="Unable to generate safe resume suggestions right now.") from exc
    optimization_id = str(uuid4())
    try:
        await create_optimization(database, {
            "optimization_id": optimization_id, "user_id": current_user.uid,
            "resume_id": job["resume_id"], "job_id": request.job_id,
            "suggestions": [item.model_dump() for item in suggestions],
            "optimized_resume": None, "before_match": match_model.model_dump(),
            "after_match": None, "generated_pdf": None, "status": "suggestions_generated",
        })
        await update_job_status(database, current_user.uid, request.job_id, "optimization_started")
    except (DuplicateKeyError, PyMongoError) as exc:
        raise _database_unavailable(exc) from exc
    return OptimizationResponse(optimization_id=optimization_id, resume_id=job["resume_id"], job_id=request.job_id, status="suggestions_generated", suggestions=suggestions)


@router.get("/{optimization_id}", response_model=OptimizationDetailResponse)
async def get_optimization(optimization_id: str, current_user: Annotated[CurrentUser, Depends(get_persisted_user)], database: Annotated[Any, Depends(require_database)]) -> OptimizationDetailResponse:
    canonical_id = _validated_id(optimization_id)
    try:
        document = await get_optimization_by_id(database, current_user.uid, canonical_id)
    except PyMongoError as exc:
        raise _database_unavailable(exc) from exc
    if not document:
        raise HTTPException(status_code=404, detail="Optimization was not found.")
    return OptimizationDetailResponse.model_validate(public_optimization(document))


@router.patch("/{optimization_id}/apply", response_model=ApplyOptimizationResponse)
async def apply_optimizations(optimization_id: str, request: ApplyPersistentOptimizationRequest, current_user: Annotated[CurrentUser, Depends(get_persisted_user)], database: Annotated[Any, Depends(require_database)]) -> ApplyOptimizationResponse:
    canonical_id = _validated_id(optimization_id)
    try:
        optimization = await get_optimization_by_id(database, current_user.uid, canonical_id)
        if not optimization:
            raise HTTPException(status_code=404, detail="Optimization was not found.")
        resume = await get_resume_by_id(database, current_user.uid, optimization["resume_id"])
        job = await get_job_by_id(database, current_user.uid, optimization["job_id"])
    except PyMongoError as exc:
        raise _database_unavailable(exc) from exc
    if not resume or not resume.get("parsed_resume") or not job or not job.get("analysis"):
        raise HTTPException(status_code=409, detail="Optimization source data is unavailable.")
    decisions = {item.id: item for item in request.suggestions}
    stored_ids = {item["id"] for item in optimization["suggestions"]}
    if any(item_id not in stored_ids for item_id in decisions):
        raise HTTPException(status_code=422, detail="One or more suggestion IDs are invalid.")
    if set(decisions) != stored_ids:
        raise HTTPException(
            status_code=422,
            detail="Review every suggestion before applying the optimization.",
        )
    merged: list[OptimizationSuggestion] = []
    for stored in optimization["suggestions"]:
        values = dict(stored)
        decision = decisions.get(stored["id"])
        if decision.status == "rejected":
            values["status"] = "rejected"
        elif decision.status == "accepted":
            values["status"] = "accepted"
        else:
            values["status"] = "edited"
            values["suggested"] = decision.edited_text
        merged.append(OptimizationSuggestion.model_validate(values))
    try:
        applied = await run_in_threadpool(
            apply_approved_suggestions,
            ResumeSchema.model_validate(resume["parsed_resume"]),
            JobAnalysisSchema.model_validate(job["analysis"]),
            merged,
        )
    except UnsafeSuggestionsError as exc:
        raise HTTPException(status_code=422, detail={"message": "One or more edited suggestions introduce information that could not be verified from the original resume.", "invalid_suggestion_ids": exc.suggestion_ids}) from exc
    try:
        await update_applied_optimization(
            database, current_user.uid, canonical_id,
            suggestions=[item.model_dump() for item in merged],
            optimized_resume=applied.optimized_resume.model_dump(),
            after_match=applied.after_match.model_dump(),
        )
    except PyMongoError as exc:
        raise _database_unavailable(exc) from exc
    before = applied.before_match.overall_score
    after = applied.after_match.overall_score
    return ApplyOptimizationResponse(optimization_id=canonical_id, status="applied", optimized_resume=applied.optimized_resume, score_comparison=ScoreComparison(before=before, after=after, change=after-before), match=applied.after_match)


@router.post("/{optimization_id}/generate-pdf", response_model=PDFGenerationResponse)
async def generate_optimized_pdf(optimization_id: str, current_user: Annotated[CurrentUser, Depends(get_persisted_user)], database: Annotated[Any, Depends(require_database)]) -> PDFGenerationResponse:
    canonical_id = _validated_id(optimization_id)
    try:
        optimization = await get_optimization_by_id(database, current_user.uid, canonical_id)
        if not optimization:
            raise HTTPException(status_code=404, detail="Optimization was not found.")
        job = await get_job_by_id(database, current_user.uid, optimization["job_id"])
    except PyMongoError as exc:
        raise _database_unavailable(exc) from exc
    if not optimization.get("optimized_resume") or not job:
        raise HTTPException(status_code=409, detail="Apply approved changes before generating a PDF.")
    resume_model = ResumeSchema.model_validate(optimization["optimized_resume"])
    key = _optimized_pdf_key(current_user.uid, optimization["resume_id"], optimization["job_id"], canonical_id)
    filename = build_resume_filename(resume_model.personal_info.name, job["company"], job["role"])
    try:
        pdf_bytes = await run_in_threadpool(generate_resume_pdf, resume_model)
        await run_in_threadpool(upload_file, file_bytes=pdf_bytes, key=key, content_type="application/pdf")
        generated_at = utc_now()
        await update_generated_pdf(database, current_user.uid, canonical_id, {"s3_key": key, "filename": filename, "generated_at": generated_at})
        await update_job_status(database, current_user.uid, optimization["job_id"], "completed")
        preview_url, download_url = await run_in_threadpool(_create_pdf_access_urls, key, filename)
    except ResumeRenderingError as exc:
        raise HTTPException(status_code=500, detail="Unable to generate the optimized resume PDF.") from exc
    except (S3ConfigurationError, S3OperationError) as exc:
        raise HTTPException(status_code=503, detail="Resume PDF storage is temporarily unavailable.") from exc
    except PyMongoError as exc:
        if not optimization.get("generated_pdf"):
            try:
                await run_in_threadpool(delete_file, key)
            except (S3ConfigurationError, S3OperationError):
                logger.exception("PDF cleanup failed after MongoDB metadata update failure.")
        raise _database_unavailable(exc) from exc
    return PDFGenerationResponse(optimization_id=canonical_id, resume_id=optimization["resume_id"], job_id=optimization["job_id"], status="generated", preview_url=preview_url, download_url=download_url, expires_in=PDF_URL_EXPIRES_IN, filename=filename)


@router.get("/{optimization_id}/pdf-access", response_model=PDFAccessResponse)
async def refresh_pdf_access(optimization_id: str, current_user: Annotated[CurrentUser, Depends(get_persisted_user)], database: Annotated[Any, Depends(require_database)]) -> PDFAccessResponse:
    canonical_id = _validated_id(optimization_id)
    try:
        optimization = await get_optimization_by_id(database, current_user.uid, canonical_id)
    except PyMongoError as exc:
        raise _database_unavailable(exc) from exc
    if not optimization or not optimization.get("generated_pdf"):
        raise HTTPException(status_code=404, detail="Generated resume PDF was not found.")
    generated = optimization["generated_pdf"]
    try:
        preview_url, download_url = await run_in_threadpool(_create_pdf_access_urls, generated["s3_key"], generated["filename"])
    except (S3ConfigurationError, S3OperationError) as exc:
        raise HTTPException(status_code=503, detail="Secure PDF access is temporarily unavailable.") from exc
    return PDFAccessResponse(optimization_id=canonical_id, resume_id=optimization["resume_id"], job_id=optimization["job_id"], status="access_refreshed", preview_url=preview_url, download_url=download_url, expires_in=PDF_URL_EXPIRES_IN, filename=generated["filename"])


@router.delete("/{optimization_id}", status_code=204)
async def delete_optimization(optimization_id: str, current_user: Annotated[CurrentUser, Depends(get_persisted_user)], database: Annotated[Any, Depends(require_database)]) -> Response:
    canonical_id = _validated_id(optimization_id)
    try:
        optimization = await get_optimization_by_id(database, current_user.uid, canonical_id)
        if not optimization:
            raise HTTPException(status_code=404, detail="Optimization was not found.")
        if optimization.get("generated_pdf"):
            try:
                await run_in_threadpool(delete_file, optimization["generated_pdf"]["s3_key"])
            except (S3ConfigurationError, S3OperationError):
                logger.exception("Generated PDF cleanup failed for optimization %s.", canonical_id)
        await delete_optimization_record(database, current_user.uid, canonical_id)
    except PyMongoError as exc:
        raise _database_unavailable(exc) from exc
    return Response(status_code=204)
