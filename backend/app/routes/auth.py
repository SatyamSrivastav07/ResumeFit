from typing import Annotated

from fastapi import APIRouter, Depends

from app.dependencies.persistence import get_persisted_user
from app.schemas.auth import CurrentUser

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.get("/me", response_model=CurrentUser)
async def read_current_user(
    current_user: Annotated[CurrentUser, Depends(get_persisted_user)],
) -> CurrentUser:
    return current_user
