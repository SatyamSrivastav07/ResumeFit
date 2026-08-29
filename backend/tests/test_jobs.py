from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes import jobs as jobs_route
from app.schemas.auth import CurrentUser
from app.schemas.job import JobAnalysisSchema
from app.services.firebase_auth import get_current_user
from app.services.mistral_service import MistralServiceError

client = TestClient(app)
RESUME_ID = str(uuid4())
VALID_DESCRIPTION = (
    "We are hiring a software engineer to build and maintain Python REST APIs. "
    "The candidate must understand PostgreSQL and Git, communicate clearly, and "
    "collaborate with engineering teams. Docker experience is preferred."
)


def valid_payload() -> dict[str, str]:
    return {
        "resume_id": RESUME_ID,
        "company": "  Example Corp  ",
        "role": "  Software Engineer  ",
        "job_description": VALID_DESCRIPTION,
    }


def mocked_analysis() -> JobAnalysisSchema:
    return JobAnalysisSchema.model_validate(
        {
            "company": "Example Corp",
            "role": "Software Engineer",
            "experience_level": "Entry Level",
            "employment_type": "Full-time",
            "required_skills": ["Python", "REST APIs"],
            "preferred_skills": ["Docker"],
            "programming_languages": ["Python"],
            "frameworks": [],
            "databases": ["PostgreSQL"],
            "cloud_and_devops": ["Docker"],
            "tools": ["Git"],
            "soft_skills": ["Communication"],
            "responsibilities": ["Build and maintain backend services"],
            "education_requirements": [],
            "experience_requirements": ["0-2 years of experience"],
            "important_keywords": ["REST APIs", "backend development"],
            "domain_keywords": [],
        }
    )


@pytest.fixture
def authenticated_user() -> None:
    async def override_current_user() -> CurrentUser:
        return CurrentUser(uid="firebase-job-user", email="user@example.com")

    app.dependency_overrides[get_current_user] = override_current_user
    yield
    app.dependency_overrides.clear()


def test_job_analysis_requires_authentication() -> None:
    response = client.post("/api/jobs/analyze", json=valid_payload())
    assert response.status_code == 401


def test_authenticated_valid_request_returns_analysis(
    authenticated_user: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    def analyze(company: str, role: str, job_description: str) -> JobAnalysisSchema:
        captured.update(company=company, role=role, job_description=job_description)
        return mocked_analysis()

    monkeypatch.setattr(jobs_route, "analyze_job_description", analyze)
    monkeypatch.setattr(jobs_route, "get_resume_by_id", lambda *_: _async_value({"status": "parsed", "parsed_resume": {"personal_info": {}}}))
    response = client.post("/api/jobs/analyze", json=valid_payload())

    assert response.status_code == 200
    body = response.json()
    UUID(body["job_id"])
    assert body["resume_id"] == RESUME_ID
    assert body["status"] == "analyzed"
    assert body["analysis"]["required_skills"] == ["Python", "REST APIs"]
    assert captured["company"] == "Example Corp"
    assert captured["role"] == "Software Engineer"
    assert "resume" not in captured


@pytest.mark.parametrize("missing_field", ["company", "role"])
def test_missing_required_text_field_returns_422(
    authenticated_user: None,
    missing_field: str,
) -> None:
    payload = valid_payload()
    payload[missing_field] = "   "
    response = client.post("/api/jobs/analyze", json=payload)
    assert response.status_code == 422


@pytest.mark.parametrize("description", ["", "Too short to be a meaningful job posting."])
def test_empty_or_short_description_returns_422(
    authenticated_user: None,
    description: str,
) -> None:
    payload = valid_payload()
    payload["job_description"] = description
    response = client.post("/api/jobs/analyze", json=payload)
    assert response.status_code == 422


def test_oversized_description_returns_422(authenticated_user: None) -> None:
    payload = valid_payload()
    payload["job_description"] = "x" * 30_001
    response = client.post("/api/jobs/analyze", json=payload)
    assert response.status_code == 422


def test_invalid_resume_id_returns_422(authenticated_user: None) -> None:
    payload = valid_payload()
    payload["resume_id"] = "not-a-uuid"
    response = client.post("/api/jobs/analyze", json=payload)
    assert response.status_code == 422


def test_mistral_failure_returns_safe_error(
    authenticated_user: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*_: str) -> JobAnalysisSchema:
        raise MistralServiceError("private provider failure details")

    monkeypatch.setattr(jobs_route, "analyze_job_description", fail)
    monkeypatch.setattr(jobs_route, "get_resume_by_id", lambda *_: _async_value({"status": "parsed", "parsed_resume": {"personal_info": {}}}))
    response = client.post("/api/jobs/analyze", json=valid_payload())

    assert response.status_code == 502
    assert response.json()["detail"] == "Unable to analyze this job right now. Please try again."
    assert response.json()["error"]["code"] == "UPSTREAM_ERROR"
    assert "private provider failure details" not in response.text


async def _async_value(value):
    return value
