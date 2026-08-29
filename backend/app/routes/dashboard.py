from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.errors import PyMongoError

from app.dependencies.persistence import get_persisted_user, require_database
from app.repositories.jobs import dashboard_history
from app.schemas.auth import CurrentUser
from app.schemas.dashboard import HistoryResponse

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/history", response_model=HistoryResponse)
async def get_history(
    current_user: Annotated[CurrentUser, Depends(get_persisted_user)],
    database: Annotated[Any, Depends(require_database)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> HistoryResponse:
    try:
        items = await dashboard_history(database, current_user.uid, limit=limit)
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="Database is temporarily unavailable. Please try again.") from exc
    return HistoryResponse(items=items)
