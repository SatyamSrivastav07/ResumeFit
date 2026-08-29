from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Resource-Policy"] = "same-site"
        if settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
            except ValueError:
                size = settings.max_json_body_bytes + 1
            is_upload = request.url.path == "/api/resumes/upload"
            maximum = settings.max_upload_size_bytes + 1_000_000 if is_upload else settings.max_json_body_bytes
            if size > maximum:
                request_id = getattr(request.state, "request_id", None)
                error = {"code": "PAYLOAD_TOO_LARGE", "message": "The request payload is too large."}
                if request_id:
                    error["request_id"] = request_id
                return JSONResponse({"error": error, "detail": error["message"]}, status_code=413)
        return await call_next(request)
