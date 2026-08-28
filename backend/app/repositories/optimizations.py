from typing import Any

from app.repositories.users import utc_now


async def create_optimization(database: Any, document: dict[str, Any]) -> None:
    now = utc_now()
    await database.optimizations.insert_one({**document, "created_at": now, "updated_at": now})


async def get_optimization_by_id(database: Any, user_id: str, optimization_id: str) -> dict[str, Any] | None:
    return await database.optimizations.find_one({"optimization_id": optimization_id, "user_id": user_id})


async def update_applied_optimization(
    database: Any,
    user_id: str,
    optimization_id: str,
    *,
    suggestions: list[dict[str, Any]],
    optimized_resume: dict[str, Any],
    after_match: dict[str, Any],
) -> bool:
    result = await database.optimizations.update_one(
        {"optimization_id": optimization_id, "user_id": user_id},
        {"$set": {
            "suggestions": suggestions,
            "optimized_resume": optimized_resume,
            "after_match": after_match,
            "status": "applied",
            "updated_at": utc_now(),
        }},
    )
    return bool(result.matched_count)


async def update_generated_pdf(
    database: Any,
    user_id: str,
    optimization_id: str,
    generated_pdf: dict[str, Any],
) -> bool:
    result = await database.optimizations.update_one(
        {"optimization_id": optimization_id, "user_id": user_id},
        {"$set": {"generated_pdf": generated_pdf, "status": "generated", "updated_at": utc_now()}},
    )
    return bool(result.matched_count)


async def list_for_resume(database: Any, user_id: str, resume_id: str) -> list[dict[str, Any]]:
    cursor = database.optimizations.find({"user_id": user_id, "resume_id": resume_id})
    return [document async for document in cursor]


async def list_for_job(database: Any, user_id: str, job_id: str) -> list[dict[str, Any]]:
    cursor = database.optimizations.find({"user_id": user_id, "job_id": job_id})
    return [document async for document in cursor]


async def delete_optimization_record(database: Any, user_id: str, optimization_id: str) -> bool:
    result = await database.optimizations.delete_one({"user_id": user_id, "optimization_id": optimization_id})
    return bool(result.deleted_count)


async def delete_for_resume(database: Any, user_id: str, resume_id: str) -> None:
    await database.optimizations.delete_many({"user_id": user_id, "resume_id": resume_id})


async def delete_for_job(database: Any, user_id: str, job_id: str) -> None:
    await database.optimizations.delete_many({"user_id": user_id, "job_id": job_id})


def public_optimization(document: dict[str, Any]) -> dict[str, Any]:
    generated = document.get("generated_pdf")
    public_generated = None
    if generated:
        public_generated = {
            "filename": generated["filename"],
            "generated_at": generated["generated_at"],
        }
    return {
        "optimization_id": document["optimization_id"],
        "resume_id": document["resume_id"],
        "job_id": document["job_id"],
        "suggestions": document.get("suggestions", []),
        "optimized_resume": document.get("optimized_resume"),
        "before_match": document.get("before_match"),
        "after_match": document.get("after_match"),
        "generated_pdf": public_generated,
        "status": document["status"],
        "created_at": document["created_at"],
        "updated_at": document["updated_at"],
    }
