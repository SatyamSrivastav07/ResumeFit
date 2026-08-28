from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes import optimizations as route
from app.schemas.auth import CurrentUser
from app.services.firebase_auth import get_current_user
from app.services.resume_matcher import calculate_resume_match
from tests.test_optimization_validator import job_fixture, resume_fixture, suggestion

client = TestClient(app)


@pytest.fixture
def authenticated_user() -> None:
    async def override() -> CurrentUser:
        return CurrentUser(uid="owner-a", email="a@example.com")
    app.dependency_overrides[get_current_user] = override
    yield
    app.dependency_overrides.clear()


def test_generate_requires_authentication() -> None:
    assert client.post("/api/optimizations/generate", json={"job_id": str(uuid4())}).status_code == 401


def test_generate_loads_owned_state_and_persists(authenticated_user, monkeypatch) -> None:
    resume = resume_fixture(); job = job_fixture(); match = calculate_resume_match(resume, job); job_id = str(uuid4()); resume_id = str(uuid4())
    monkeypatch.setattr(route, "get_job_by_id", lambda *_: async_value({"job_id": job_id, "resume_id": resume_id, "analysis": job.model_dump(), "match_analysis": match.model_dump()}))
    monkeypatch.setattr(route, "get_resume_by_id", lambda *_: async_value({"parsed_resume": resume.model_dump()}))
    monkeypatch.setattr(route, "generate_resume_suggestions", lambda *_: [suggestion()])
    response = client.post("/api/optimizations/generate", json={"job_id": job_id})
    assert response.status_code == 200
    assert response.json()["status"] == "suggestions_generated"


def test_apply_accepts_only_compact_decisions(authenticated_user, monkeypatch) -> None:
    resume = resume_fixture(); job = job_fixture(); item = suggestion(); optimization_id = str(uuid4())
    monkeypatch.setattr(route, "get_optimization_by_id", lambda *_: async_value({"optimization_id": optimization_id, "resume_id": str(uuid4()), "job_id": str(uuid4()), "suggestions": [item.model_dump()]}))
    monkeypatch.setattr(route, "get_resume_by_id", lambda *_: async_value({"parsed_resume": resume.model_dump()}))
    monkeypatch.setattr(route, "get_job_by_id", lambda *_: async_value({"analysis": job.model_dump()}))
    response = client.patch(f"/api/optimizations/{optimization_id}/apply", json={"suggestions": [{"id": item.id, "status": "accepted", "edited_text": None}]})
    assert response.status_code == 200
    assert response.json()["status"] == "applied"


def test_apply_rejects_tampered_decision_fields(authenticated_user) -> None:
    response = client.patch(f"/api/optimizations/{uuid4()}/apply", json={"suggestions": [{"id": str(uuid4()), "status": "accepted", "edited_text": None, "section": "summary"}]})
    assert response.status_code == 422


def test_apply_requires_a_decision_for_every_suggestion(authenticated_user, monkeypatch) -> None:
    resume = resume_fixture(); job = job_fixture(); first = suggestion(); second = suggestion(); optimization_id = str(uuid4())
    monkeypatch.setattr(route, "get_optimization_by_id", lambda *_: async_value({"optimization_id": optimization_id, "resume_id": str(uuid4()), "job_id": str(uuid4()), "suggestions": [first.model_dump(), second.model_dump()]}))
    monkeypatch.setattr(route, "get_resume_by_id", lambda *_: async_value({"parsed_resume": resume.model_dump()}))
    monkeypatch.setattr(route, "get_job_by_id", lambda *_: async_value({"analysis": job.model_dump()}))

    response = client.patch(
        f"/api/optimizations/{optimization_id}/apply",
        json={"suggestions": [{"id": first.id, "status": "accepted", "edited_text": None}]},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Review every suggestion before applying the optimization."


async def async_value(value):
    return value
