from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
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
) -> HistoryResponse:
    try:
        items = await dashboard_history(database, current_user.uid, limit=20)
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="Database is temporarily unavailable. Please try again.") from exc
    return HistoryResponse(items=items)
