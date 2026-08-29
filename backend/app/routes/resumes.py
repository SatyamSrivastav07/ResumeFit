import logging
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from pymongo.errors import DuplicateKeyError, PyMongoError
from starlette.concurrency import run_in_threadpool

from app.dependencies.persistence import get_persisted_user, require_database
from app.config import settings
from app.core.rate_limit import ai_rate_limit, upload_rate_limit
from app.repositories.jobs import delete_jobs_for_resume
from app.repositories.optimizations import delete_for_resume, list_for_resume
from app.repositories.resumes import create_resume, delete_resume_record, get_resume_by_id, list_user_resumes, mark_parse_failed, public_resume, update_parsed_resume
from app.schemas.auth import CurrentUser
from app.schemas.resume import ResumeDetailResponse, ResumeListResponse, ResumeParseResponse, ResumePDFAccessResponse, ResumeUploadResponse
from app.services.mistral_service import MistralConfigurationError, MistralResponseError, MistralServiceError, parse_resume_text
from app.services.pdf_parser import PDFParseError, extract_text_from_pdf
from app.services.s3_service import S3ConfigurationError, S3ObjectNotFoundError, S3OperationError, delete_file, download_file, generate_presigned_url, upload_file

router = APIRouter(prefix="/api/resumes", tags=["Resumes"])
logger = logging.getLogger(__name__)
MAX_PDF_SIZE = settings.max_upload_size_bytes
PDF_CONTENT_TYPE = "application/pdf"
PDF_URL_EXPIRES_IN = settings.presigned_url_expiry_seconds


def _safe_display_filename(filename: str | None) -> str:
    if not filename:
        return "resume.pdf"
    basename = filename.replace("\\", "/").rsplit("/", maxsplit=1)[-1]
    sanitized = basename.replace("\x00", "").replace("\r", "").replace("\n", "")
    return sanitized[:255] or "resume.pdf"


def _canonical_resume_id(resume_id: str) -> str:
    try:
        parsed = UUID(resume_id)
    except (ValueError, AttributeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid resume ID.") from exc
    canonical = str(parsed)
    if canonical != resume_id.lower():
        raise HTTPException(status_code=400, detail="Invalid resume ID.")
    return canonical


def _database_unavailable(exc: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail="Database is temporarily unavailable. Please try again.")


@router.post("/upload", response_model=ResumeUploadResponse, dependencies=[Depends(upload_rate_limit)])
async def upload_resume(
    current_user: Annotated[CurrentUser, Depends(get_persisted_user)],
    database: Annotated[Any, Depends(require_database)],
    file: Annotated[UploadFile, File(description="PDF resume, maximum 5 MB")],
) -> ResumeUploadResponse:
    if file.filename and len(file.filename.encode("utf-8")) > 255:
        await file.close()
        raise HTTPException(status_code=400, detail="The uploaded filename is too long.")
    filename = _safe_display_filename(file.filename)
    if not filename.lower().endswith(".pdf") or file.content_type != PDF_CONTENT_TYPE:
        raise HTTPException(status_code=400, detail="Only PDF resume files are accepted.")
    try:
        file_bytes = await file.read(MAX_PDF_SIZE + 1)
    except OSError as exc:
        raise HTTPException(status_code=400, detail="The uploaded file could not be read.") from exc
    finally:
        await file.close()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="The uploaded PDF is empty.")
    if len(file_bytes) > MAX_PDF_SIZE:
        raise HTTPException(status_code=413, detail="The PDF must be 5 MB or smaller.")
    if not file_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF.")

    resume_id = str(uuid4())
    s3_key = f"users/{current_user.uid}/resumes/{resume_id}/original.pdf"
    try:
        await run_in_threadpool(upload_file, file_bytes=file_bytes, key=s3_key, content_type=PDF_CONTENT_TYPE)
    except S3ConfigurationError as exc:
        raise HTTPException(status_code=503, detail="Resume storage is not configured.") from exc
    except S3OperationError as exc:
        raise HTTPException(status_code=503, detail="Unable to upload resume. Please try again.") from exc

    try:
        await create_resume(database, {
            "resume_id": resume_id, "user_id": current_user.uid,
            "original_filename": filename, "original_s3_key": s3_key,
            "file_size": len(file_bytes), "content_type": PDF_CONTENT_TYPE,
            "status": "uploaded", "parsed_resume": None,
        })
    except (DuplicateKeyError, PyMongoError) as exc:
        try:
            await run_in_threadpool(delete_file, s3_key)
        except (S3ConfigurationError, S3OperationError):
            logger.exception("Failed to compensate S3 upload after MongoDB insert failure.")
        raise _database_unavailable(exc) from exc

    return ResumeUploadResponse(resume_id=resume_id, filename=filename, size=len(file_bytes), content_type=PDF_CONTENT_TYPE, status="uploaded")


@router.get("", response_model=ResumeListResponse)
async def list_resumes(
    current_user: Annotated[CurrentUser, Depends(get_persisted_user)],
    database: Annotated[Any, Depends(require_database)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ResumeListResponse:
    try:
        documents = await list_user_resumes(database, current_user.uid, limit=limit)
    except PyMongoError as exc:
        raise _database_unavailable(exc) from exc
    return ResumeListResponse(items=[{
        "resume_id": item["resume_id"], "filename": item["original_filename"], "status": item["status"],
        "created_at": item["created_at"], "updated_at": item["updated_at"],
    } for item in documents])


@router.get("/{resume_id}", response_model=ResumeDetailResponse)
async def get_resume(resume_id: str, current_user: Annotated[CurrentUser, Depends(get_persisted_user)], database: Annotated[Any, Depends(require_database)]) -> ResumeDetailResponse:
    canonical_id = _canonical_resume_id(resume_id)
    try:
        document = await get_resume_by_id(database, current_user.uid, canonical_id)
    except PyMongoError as exc:
        raise _database_unavailable(exc) from exc
    if not document:
        raise HTTPException(status_code=404, detail="Resume was not found.")
    return ResumeDetailResponse.model_validate(public_resume(document))


@router.get("/{resume_id}/pdf-access", response_model=ResumePDFAccessResponse)
async def refresh_resume_pdf_access(
    resume_id: str,
    current_user: Annotated[CurrentUser, Depends(get_persisted_user)],
    database: Annotated[Any, Depends(require_database)],
) -> ResumePDFAccessResponse:
    canonical_id = _canonical_resume_id(resume_id)
    try:
        document = await get_resume_by_id(database, current_user.uid, canonical_id)
    except PyMongoError as exc:
        raise _database_unavailable(exc) from exc
    if not document:
        raise HTTPException(status_code=404, detail="Resume was not found.")
    filename = _safe_display_filename(document.get("original_filename"))
    try:
        preview_url = await run_in_threadpool(
            generate_presigned_url,
            document["original_s3_key"],
            expires_in=PDF_URL_EXPIRES_IN,
            response_content_disposition="inline",
            response_content_type=PDF_CONTENT_TYPE,
        )
        download_url = await run_in_threadpool(
            generate_presigned_url,
            document["original_s3_key"],
            expires_in=PDF_URL_EXPIRES_IN,
            response_content_disposition=f'attachment; filename="{filename}"',
            response_content_type=PDF_CONTENT_TYPE,
        )
    except S3ConfigurationError as exc:
        raise HTTPException(status_code=503, detail="Resume storage is not configured.") from exc
    except S3OperationError as exc:
        raise HTTPException(status_code=503, detail="Unable to access the saved resume.") from exc
    return ResumePDFAccessResponse(
        resume_id=canonical_id,
        status="access_refreshed",
        preview_url=preview_url,
        download_url=download_url,
        expires_in=PDF_URL_EXPIRES_IN,
        filename=filename,
    )


@router.post("/{resume_id}/parse", response_model=ResumeParseResponse, dependencies=[Depends(ai_rate_limit)])
async def parse_resume(resume_id: str, current_user: Annotated[CurrentUser, Depends(get_persisted_user)], database: Annotated[Any, Depends(require_database)]) -> ResumeParseResponse:
    canonical_id = _canonical_resume_id(resume_id)
    try:
        document = await get_resume_by_id(database, current_user.uid, canonical_id)
    except PyMongoError as exc:
        raise _database_unavailable(exc) from exc
    if not document:
        raise HTTPException(status_code=404, detail="Resume was not found.")
    if document.get("parsed_resume") and document.get("status") == "parsed":
        return ResumeParseResponse(resume_id=canonical_id, status="parsed", resume=document["parsed_resume"])
    try:
        pdf_bytes = await run_in_threadpool(download_file, document["original_s3_key"])
    except S3ObjectNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Resume was not found.") from exc
    except S3ConfigurationError as exc:
        raise HTTPException(status_code=503, detail="Resume storage is not configured.") from exc
    except S3OperationError as exc:
        raise HTTPException(status_code=503, detail="Unable to retrieve resume. Please try again.") from exc
    try:
        resume_text = await run_in_threadpool(extract_text_from_pdf, pdf_bytes)
        parsed_resume = await run_in_threadpool(parse_resume_text, resume_text)
    except PDFParseError as exc:
        await mark_parse_failed(database, current_user.uid, canonical_id)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except MistralConfigurationError as exc:
        raise HTTPException(status_code=503, detail="Resume parsing service is not configured.") from exc
    except (MistralResponseError, MistralServiceError) as exc:
        await mark_parse_failed(database, current_user.uid, canonical_id)
        raise HTTPException(status_code=502, detail="Unable to parse this resume right now. Please try again.") from exc
    try:
        await update_parsed_resume(database, current_user.uid, canonical_id, parsed_resume.model_dump())
    except PyMongoError as exc:
        raise _database_unavailable(exc) from exc
    return ResumeParseResponse(resume_id=canonical_id, status="parsed", resume=parsed_resume)


@router.delete("/{resume_id}", status_code=204)
async def delete_resume(resume_id: str, current_user: Annotated[CurrentUser, Depends(get_persisted_user)], database: Annotated[Any, Depends(require_database)]) -> Response:
    canonical_id = _canonical_resume_id(resume_id)
    try:
        document = await get_resume_by_id(database, current_user.uid, canonical_id)
        if not document:
            raise HTTPException(status_code=404, detail="Resume was not found.")
        optimizations = await list_for_resume(database, current_user.uid, canonical_id)
        keys = [document["original_s3_key"]] + [item["generated_pdf"]["s3_key"] for item in optimizations if item.get("generated_pdf")]
        for key in keys:
            try:
                await run_in_threadpool(delete_file, key)
            except (S3ConfigurationError, S3OperationError):
                logger.exception("S3 cleanup failed while deleting resume %s.", canonical_id)
        await delete_for_resume(database, current_user.uid, canonical_id)
        await delete_jobs_for_resume(database, current_user.uid, canonical_id)
        await delete_resume_record(database, current_user.uid, canonical_id)
    except PyMongoError as exc:
        raise _database_unavailable(exc) from exc
    return Response(status_code=204)
