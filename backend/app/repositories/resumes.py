from datetime import datetime
from typing import Any

from app.repositories.users import utc_now


async def create_resume(database: Any, document: dict[str, Any]) -> None:
    now = utc_now()
    await database.resumes.insert_one({**document, "created_at": now, "updated_at": now})


async def get_resume_by_id(database: Any, user_id: str, resume_id: str) -> dict[str, Any] | None:
    return await database.resumes.find_one({"resume_id": resume_id, "user_id": user_id})


async def update_parsed_resume(database: Any, user_id: str, resume_id: str, parsed_resume: dict[str, Any]) -> bool:
    result = await database.resumes.update_one(
        {"resume_id": resume_id, "user_id": user_id},
        {"$set": {"parsed_resume": parsed_resume, "status": "parsed", "updated_at": utc_now()}},
    )
    return bool(result.matched_count)


async def mark_parse_failed(database: Any, user_id: str, resume_id: str) -> None:
    await database.resumes.update_one(
        {"resume_id": resume_id, "user_id": user_id},
        {"$set": {"status": "parse_failed", "updated_at": utc_now()}},
    )


async def list_user_resumes(database: Any, user_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
    cursor = database.resumes.find(
        {"user_id": user_id},
        {"_id": 0, "parsed_resume": 0, "original_s3_key": 0},
    ).sort([("created_at", -1), ("resume_id", -1)]).limit(limit)
    return [document async for document in cursor]


async def delete_resume_record(database: Any, user_id: str, resume_id: str) -> bool:
    result = await database.resumes.delete_one({"resume_id": resume_id, "user_id": user_id})
    return bool(result.deleted_count)


def public_resume(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "resume_id": document["resume_id"],
        "filename": document["original_filename"],
        "status": document["status"],
        "parsed_resume": document.get("parsed_resume"),
        "created_at": document["created_at"],
        "updated_at": document["updated_at"],
    }
