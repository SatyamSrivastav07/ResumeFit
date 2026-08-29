from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import PyMongoError

from app.dependencies.persistence import require_database
from app.schemas.health import HealthResponse, ReadinessResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check(
    database: Annotated[Any, Depends(require_database)],
) -> ReadinessResponse:
    try:
        await database.command("ping")
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="Application dependencies are not ready.") from exc
    return ReadinessResponse(status="ready", services={"database": "ok"})
