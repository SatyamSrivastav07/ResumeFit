from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from pymongo.errors import PyMongoError

from app.database.mongodb import DatabaseConfigurationError, get_database
from app.repositories.users import ensure_user_exists
from app.schemas.auth import CurrentUser
from app.services.firebase_auth import get_current_user


def require_database() -> Any:
    try:
        return get_database()
    except DatabaseConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is temporarily unavailable. Please try again.",
        ) from exc


async def get_persisted_user(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    database: Annotated[Any, Depends(require_database)],
) -> CurrentUser:
    try:
        await ensure_user_exists(database, current_user)
    except PyMongoError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is temporarily unavailable. Please try again.",
        ) from exc
    return current_user
