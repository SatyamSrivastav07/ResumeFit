import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.auth import CurrentUser
from app.services.firebase_auth import get_current_user

client = TestClient(app)


def authenticate(uid: str) -> None:
    async def override() -> CurrentUser:
        return CurrentUser(uid=uid, email=f"{uid}@example.com")
    app.dependency_overrides[get_current_user] = override


def test_user_is_upserted_on_protected_request(isolated_database) -> None:
    authenticate("new-user")
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    document = asyncio.run(isolated_database.users.find_one({"firebase_uid": "new-user"}))
    assert document["email"] == "new-user@example.com"
    app.dependency_overrides.pop(get_current_user, None)


def test_resume_idor_get_and_delete_return_404(isolated_database) -> None:
    resume_id = str(uuid4()); now = datetime.now(timezone.utc)
    asyncio.run(isolated_database.resumes.insert_one({"resume_id": resume_id, "user_id": "owner-a", "original_filename": "private.pdf", "original_s3_key": "private/key", "status": "parsed", "parsed_resume": {"personal_info": {}}, "created_at": now, "updated_at": now}))
    authenticate("owner-b")
    assert client.get(f"/api/resumes/{resume_id}").status_code == 404
    assert client.delete(f"/api/resumes/{resume_id}").status_code == 404
    app.dependency_overrides.pop(get_current_user, None)


def test_job_idor_returns_404(isolated_database) -> None:
    job_id = str(uuid4()); now = datetime.now(timezone.utc)
    asyncio.run(isolated_database.jobs.insert_one({"job_id": job_id, "resume_id": str(uuid4()), "user_id": "owner-a", "company": "Private", "role": "Engineer", "job_description": "private", "analysis": {}, "status": "analyzed", "created_at": now, "updated_at": now}))
    authenticate("owner-b")
    assert client.get(f"/api/jobs/{job_id}").status_code == 404
    assert client.post(f"/api/jobs/{job_id}/match").status_code == 404
    app.dependency_overrides.pop(get_current_user, None)


def test_history_is_owner_scoped_and_sorted_newest_first(isolated_database) -> None:
    now = datetime.now(timezone.utc); resume_a = str(uuid4()); resume_b = str(uuid4()); old_job = str(uuid4()); new_job = str(uuid4())
    async def seed() -> None:
        await isolated_database.resumes.insert_many([
            {"resume_id": resume_a, "user_id": "owner-a", "original_filename": "a.pdf", "created_at": now, "updated_at": now},
            {"resume_id": resume_b, "user_id": "owner-b", "original_filename": "b.pdf", "created_at": now, "updated_at": now},
        ])
        await isolated_database.jobs.insert_many([
            {"job_id": old_job, "resume_id": resume_a, "user_id": "owner-a", "company": "Old Co", "role": "Engineer", "status": "matched", "match_analysis": {"overall_score": 50}, "created_at": now - timedelta(days=1), "updated_at": now},
            {"job_id": new_job, "resume_id": resume_a, "user_id": "owner-a", "company": "New Co", "role": "Senior Engineer", "status": "matched", "match_analysis": {"overall_score": 70}, "created_at": now, "updated_at": now},
            {"job_id": str(uuid4()), "resume_id": resume_b, "user_id": "owner-b", "company": "Secret Co", "role": "Private", "status": "matched", "created_at": now + timedelta(days=1), "updated_at": now},
        ])
    asyncio.run(seed()); authenticate("owner-a")
    response = client.get("/api/dashboard/history")
    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["company"] for item in items] == ["New Co", "Old Co"]
    assert all(item["company"] != "Secret Co" for item in items)
    app.dependency_overrides.pop(get_current_user, None)
