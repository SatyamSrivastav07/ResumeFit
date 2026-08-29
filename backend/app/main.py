import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.config import settings
from app.core.error_handlers import register_error_handlers
from app.core.logging import configure_logging
from app.core.rate_limit import authenticated_rate_limit
from app.database.mongodb import close_mongodb, initialize_mongodb
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.security import RequestSizeLimitMiddleware, SecurityHeadersMiddleware
from app.routes.auth import router as auth_router
from app.routes.dashboard import router as dashboard_router
from app.routes.health import router as health_router
from app.routes.jobs import router as jobs_router
from app.routes.match import router as match_router
from app.routes.optimizations import router as optimizations_router
from app.routes.resumes import router as resumes_router

logger = logging.getLogger(__name__)
configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        await initialize_mongodb()
    except Exception:
        if settings.app_env == "production":
            logger.exception("Production startup aborted because MongoDB is unavailable.")
            raise
        logger.warning("Application started without an available MongoDB connection.")
    yield
    await close_mongodb()


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="API for ResumeFit AI.",
        lifespan=lifespan,
        docs_url="/docs" if settings.enable_api_docs else None,
        redoc_url="/redoc" if settings.enable_api_docs else None,
        openapi_url="/openapi.json" if settings.enable_api_docs else None,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )
    application.add_middleware(GZipMiddleware, minimum_size=1_000)
    application.add_middleware(RequestSizeLimitMiddleware)
    application.add_middleware(RequestContextMiddleware)
    application.add_middleware(SecurityHeadersMiddleware)
    register_error_handlers(application)

    application.include_router(health_router)
    authenticated_dependencies = [Depends(authenticated_rate_limit)]
    application.include_router(auth_router, dependencies=authenticated_dependencies)
    application.include_router(resumes_router, dependencies=authenticated_dependencies)
    application.include_router(jobs_router, dependencies=authenticated_dependencies)
    application.include_router(match_router, dependencies=authenticated_dependencies)  # Legacy Phase 6 compatibility.
    application.include_router(dashboard_router, dependencies=authenticated_dependencies)
    application.include_router(optimizations_router, dependencies=authenticated_dependencies)
    return application


app = create_app()
