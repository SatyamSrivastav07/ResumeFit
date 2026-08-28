import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.mongodb import close_mongodb, initialize_mongodb
from app.routes.auth import router as auth_router
from app.routes.dashboard import router as dashboard_router
from app.routes.health import router as health_router
from app.routes.jobs import router as jobs_router
from app.routes.match import router as match_router
from app.routes.optimizations import router as optimizations_router
from app.routes.resumes import router as resumes_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        await initialize_mongodb()
    except Exception:
        logger.warning("Application started without an available MongoDB connection.")
    yield
    await close_mongodb()


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="API for ResumeFit AI.",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(resumes_router)
    application.include_router(jobs_router)
    application.include_router(match_router)  # Legacy Phase 6 compatibility; frontend uses /api/jobs/{job_id}/match.
    application.include_router(dashboard_router)
    application.include_router(optimizations_router)
    return application


app = create_app()
