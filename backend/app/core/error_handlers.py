import logging

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import ApplicationError

logger = logging.getLogger(__name__)


def _payload(code: str, message: str, request: Request, *, detail: object | None = None) -> dict:
    request_id = getattr(request.state, "request_id", None)
    error = {"code": code, "message": message}
    if request_id:
        error["request_id"] = request_id
    return {"error": error, "detail": message if detail is None else detail}


async def application_error_handler(request: Request, exc: ApplicationError) -> JSONResponse:
    return JSONResponse(_payload(exc.code, exc.message, request), status_code=exc.status_code, headers=exc.headers)


async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    message = str(detail.get("message") or "The request could not be completed.") if isinstance(detail, dict) else str(detail)
    codes = {400: "BAD_REQUEST", 401: "AUTHENTICATION_REQUIRED", 403: "FORBIDDEN", 404: "RESOURCE_NOT_FOUND", 409: "CONFLICT", 413: "PAYLOAD_TOO_LARGE", 422: "VALIDATION_ERROR", 429: "RATE_LIMIT_EXCEEDED", 500: "INTERNAL_ERROR", 502: "UPSTREAM_ERROR", 503: "SERVICE_UNAVAILABLE", 504: "UPSTREAM_TIMEOUT"}
    return JSONResponse(_payload(codes.get(exc.status_code, "REQUEST_FAILED"), message, request, detail=detail), status_code=exc.status_code, headers=exc.headers)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.info("Request validation failed.")
    return JSONResponse(_payload("VALIDATION_ERROR", "The request contains invalid or missing fields.", request), status_code=422)


async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled application error.")
    return JSONResponse(_payload("INTERNAL_ERROR", "An unexpected error occurred.", request), status_code=500)


def register_error_handlers(application) -> None:
    application.add_exception_handler(ApplicationError, application_error_handler)
    application.add_exception_handler(HTTPException, http_error_handler)
    application.add_exception_handler(RequestValidationError, validation_error_handler)
    application.add_exception_handler(Exception, unexpected_error_handler)
