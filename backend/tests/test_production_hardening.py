import base64
import json
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings, settings
from app.core.rate_limit import limiter
from app.main import app
from app.routes import resumes as resumes_route
from app.schemas.auth import CurrentUser
from app.schemas.resume import ResumeSchema
from app.services.firebase_auth import get_current_user

client = TestClient(app)


def test_health_has_request_id_and_security_headers() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    UUID(response.headers["x-request-id"])
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"


def test_readiness_checks_database() -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "services": {"database": "ok"}}


def test_production_configuration_fails_when_critical_secrets_are_missing() -> None:
    with pytest.raises(ValidationError, match="Missing production configuration"):
        Settings(_env_file=None, app_env="production", frontend_url="https://resume.example.com")


def test_development_configuration_allows_localhost_without_live_services() -> None:
    configured = Settings(_env_file=None, app_env="development", frontend_url="http://localhost:5173")
    assert configured.allowed_origins == ["http://localhost:5173"]


def test_production_configuration_accepts_base64_firebase_credentials() -> None:
    service_account = {"type": "service_account", "project_id": "resume-fit-test"}
    encoded = base64.b64encode(json.dumps(service_account).encode()).decode()

    configured = Settings(
        _env_file=None,
        app_env="production",
        frontend_url="https://resume.example.com",
        mongodb_uri="mongodb://database.example.com",
        mistral_api_key="test-key",
        aws_region="ap-south-1",
        aws_s3_bucket="resume-test",
        firebase_credentials_base64=encoded,
    )

    assert configured.firebase_credentials_from_base64() == service_account


def test_aws_static_credentials_must_be_configured_as_a_pair() -> None:
    with pytest.raises(ValidationError, match="must be configured together"):
        Settings(
            _env_file=None,
            app_env="development",
            frontend_url="http://localhost:5173",
            aws_access_key_id="access-only",
        )


def test_expensive_route_returns_429_with_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    async def current_user() -> CurrentUser:
        return CurrentUser(uid="rate-limit-owner", email="owner@example.com")

    parsed = ResumeSchema.model_validate({"personal_info": {"name": "Candidate"}})

    async def stored_resume(*_: object) -> dict:
        return {"status": "parsed", "parsed_resume": parsed.model_dump()}

    limiter.clear()
    monkeypatch.setattr(settings, "rate_limit_ai", 1)
    app.dependency_overrides[get_current_user] = current_user
    monkeypatch.setattr(resumes_route, "get_resume_by_id", stored_resume)
    resume_id = str(uuid4())
    try:
        first = client.post(f"/api/resumes/{resume_id}/parse")
        second = client.post(f"/api/resumes/{resume_id}/parse")
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        limiter.clear()

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert int(second.headers["retry-after"]) >= 1


def test_oversized_json_is_rejected_before_route_processing() -> None:
    response = client.post(
        "/api/jobs/analyze",
        content=b"x" * (settings.max_json_body_bytes + 1),
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    UUID(response.headers["x-request-id"])
