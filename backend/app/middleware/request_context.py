import logging
import time
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import request_id_context

logger = logging.getLogger("resumefit.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid4())
        request.state.request_id = request_id
        token = request_id_context.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            route = request.scope.get("route")
            route_path = getattr(route, "path", request.url.path)
            status_code = getattr(locals().get("response"), "status_code", 500)
            extra = {"method": request.method, "route": route_path, "status_code": status_code, "duration_ms": duration_ms}
            user_ref = getattr(request.state, "user_ref", None)
            if user_ref:
                extra["user_ref"] = user_ref
            logger.info(
                "request_complete",
                extra=extra,
            )
            if "response" in locals():
                response.headers["X-Request-ID"] = request_id
            request_id_context.reset(token)
