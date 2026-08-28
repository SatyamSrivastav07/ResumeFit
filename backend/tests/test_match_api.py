from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.auth import CurrentUser
from app.services.firebase_auth import get_current_user

client = TestClient(app)


def valid_payload() -> dict[str, object]:
    return {
        "resume_id": str(uuid4()),
        "job_id": str(uuid4()),
        "resume": {
            "personal_info": {"name": "Candidate", "email": "candidate@example.com"},
            "summary": "Python backend engineer",
            "skills": {"technical": ["Python", "REST APIs"], "tools": ["Git"], "soft": []},
            "experience": [
                {
                    "company": "Example Corp",
                    "role": "Software Engineer",
                    "description": ["Built REST APIs using Python."],
                }
            ],
            "projects": [],
            "education": [],
            "certifications": [],
            "achievements": [],
            "languages": [],
        },
        "job": {
            "company": "Example Corp",
            "role": "Software Engineer",
            "experience_level": "Entry Level",
            "employment_type": "Full-time",
            "required_skills": ["Python", "REST APIs"],
            "preferred_skills": ["Docker"],
            "programming_languages": ["Python"],
            "frameworks": [],
            "databases": [],
            "cloud_and_devops": ["Docker"],
            "tools": ["Git"],
            "soft_skills": [],
            "responsibilities": ["Build backend services"],
            "education_requirements": [],
            "experience_requirements": [],
            "important_keywords": ["REST APIs"],
            "domain_keywords": [],
        },
    }


@pytest.fixture
def authenticated_user() -> None:
    async def override_current_user() -> CurrentUser:
        return CurrentUser(uid="firebase-match-user", email="user@example.com")

    app.dependency_overrides[get_current_user] = override_current_user
    yield
    app.dependency_overrides.clear()


def test_match_requires_authentication() -> None:
    response = client.post("/api/match/analyze", json=valid_payload())
    assert response.status_code == 401


def test_valid_authenticated_match_returns_200(authenticated_user: None) -> None:
    payload = valid_payload()
    response = client.post("/api/match/analyze", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["resume_id"] == payload["resume_id"]
    assert body["job_id"] == payload["job_id"]
    assert body["status"] == "matched"
    assert 0 <= body["match"]["overall_score"] <= 100
    assert body["match"]["breakdown"]["skills"]["max_score"] == 40


def test_malformed_resume_returns_422(authenticated_user: None) -> None:
    payload = valid_payload()
    payload["resume"]["experience"] = [{"role": "Engineer"}]
    response = client.post("/api/match/analyze", json=payload)
    assert response.status_code == 422


def test_malformed_job_returns_422(authenticated_user: None) -> None:
    payload = valid_payload()
    del payload["job"]["company"]
    response = client.post("/api/match/analyze", json=payload)
    assert response.status_code == 422


@pytest.mark.parametrize("field", ["resume_id", "job_id"])
def test_invalid_identifier_returns_422(
    authenticated_user: None,
    field: str,
) -> None:
    payload = valid_payload()
    payload[field] = "not-a-uuid"
    response = client.post("/api/match/analyze", json=payload)
    assert response.status_code == 422
