from typing import Any

from app.repositories.users import utc_now


async def create_job(database: Any, document: dict[str, Any]) -> None:
    now = utc_now()
    await database.jobs.insert_one({**document, "created_at": now, "updated_at": now})


async def get_job_by_id(database: Any, user_id: str, job_id: str) -> dict[str, Any] | None:
    return await database.jobs.find_one({"job_id": job_id, "user_id": user_id})


async def update_match(database: Any, user_id: str, job_id: str, match_analysis: dict[str, Any]) -> bool:
    result = await database.jobs.update_one(
        {"job_id": job_id, "user_id": user_id},
        {"$set": {"match_analysis": match_analysis, "status": "matched", "updated_at": utc_now()}},
    )
    return bool(result.matched_count)


async def update_job_status(database: Any, user_id: str, job_id: str, value: str) -> None:
    await database.jobs.update_one(
        {"job_id": job_id, "user_id": user_id},
        {"$set": {"status": value, "updated_at": utc_now()}},
    )


async def list_user_jobs(database: Any, user_id: str, *, resume_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    query: dict[str, Any] = {"user_id": user_id}
    if resume_id:
        query["resume_id"] = resume_id
    cursor = database.jobs.find(query, {"_id": 0}).sort("created_at", -1).limit(limit)
    return [document async for document in cursor]


async def delete_jobs_for_resume(database: Any, user_id: str, resume_id: str) -> None:
    await database.jobs.delete_many({"user_id": user_id, "resume_id": resume_id})


async def delete_job_record(database: Any, user_id: str, job_id: str) -> bool:
    result = await database.jobs.delete_one({"user_id": user_id, "job_id": job_id})
    return bool(result.deleted_count)


async def dashboard_history(database: Any, user_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    jobs = await list_user_jobs(database, user_id, limit=limit)
    if not jobs:
        return []
    resume_ids = list({item["resume_id"] for item in jobs})
    job_ids = [item["job_id"] for item in jobs]
    resume_cursor = database.resumes.find(
        {"user_id": user_id, "resume_id": {"$in": resume_ids}},
        {"resume_id": 1, "original_filename": 1},
    )
    resumes = {item["resume_id"]: item async for item in resume_cursor}
    optimization_cursor = database.optimizations.find(
        {"user_id": user_id, "job_id": {"$in": job_ids}},
    ).sort("created_at", -1)
    latest_optimizations: dict[str, dict[str, Any]] = {}
    async for item in optimization_cursor:
        latest_optimizations.setdefault(item["job_id"], item)

    history: list[dict[str, Any]] = []
    for job in jobs:
        optimization = latest_optimizations.get(job["job_id"])
        before = optimization.get("before_match") if optimization else job.get("match_analysis")
        after = optimization.get("after_match") if optimization else None
        history.append({
            "job_id": job["job_id"],
            "resume_id": job["resume_id"],
            "optimization_id": optimization.get("optimization_id") if optimization else None,
            "company": job["company"],
            "role": job["role"],
            "resume_filename": resumes.get(job["resume_id"], {}).get("original_filename", "Resume"),
            "before_score": before.get("overall_score") if before else None,
            "after_score": after.get("overall_score") if after else None,
            "status": optimization.get("status") if optimization else job["status"],
            "has_pdf": bool(optimization and optimization.get("generated_pdf")),
            "created_at": job["created_at"],
        })
    return history
