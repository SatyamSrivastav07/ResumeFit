from datetime import datetime, timezone
from typing import Any

from app.schemas.auth import CurrentUser


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def ensure_user_exists(database: Any, current_user: CurrentUser) -> None:
    now = utc_now()
    updates: dict[str, Any] = {"updated_at": now}
    if current_user.email:
        updates["email"] = current_user.email
    await database.users.update_one(
        {"firebase_uid": current_user.uid},
        {
            "$set": updates,
            "$setOnInsert": {
                "firebase_uid": current_user.uid,
                "display_name": None,
                "created_at": now,
            },
        },
        upsert=True,
    )
