from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes import optimizations as route
from app.schemas.auth import CurrentUser
from app.services.firebase_auth import get_current_user
from app.services.s3_service import S3OperationError

client = TestClient(app)


@pytest.fixture
def authenticated_user():
    async def override(): return CurrentUser(uid="pdf-owner", email="owner@example.com")
    app.dependency_overrides[get_current_user] = override
    yield
    app.dependency_overrides.clear()


def optimization_record(optimization_id: str) -> dict:
    return {"optimization_id": optimization_id, "resume_id": str(uuid4()), "job_id": str(uuid4()), "optimized_resume": {"personal_info": {"name": "Test User"}, "skills": {}, "experience": [], "projects": [], "education": []}, "generated_pdf": None}


def test_generate_requires_authentication():
    assert client.post(f"/api/optimizations/{uuid4()}/generate-pdf").status_code == 401


def test_generate_uses_stored_resume_and_owner_scoped_key(authenticated_user, monkeypatch):
    optimization_id = str(uuid4()); record = optimization_record(optimization_id); captured = {}
    monkeypatch.setattr(route, "get_optimization_by_id", lambda *_: async_value(record))
    monkeypatch.setattr(route, "get_job_by_id", lambda *_: async_value({"company": "Example", "role": "Engineer"}))
    monkeypatch.setattr(route, "generate_resume_pdf", lambda _: b"%PDF-" + b"x" * 1500)
    monkeypatch.setattr(route, "upload_file", lambda **kwargs: captured.update(kwargs))
    monkeypatch.setattr(route, "generate_presigned_url", lambda key, **kwargs: f"https://signed/{'download' if str(kwargs.get('response_content_disposition')).startswith('attachment') else 'preview'}")
    response = client.post(f"/api/optimizations/{optimization_id}/generate-pdf")
    assert response.status_code == 200
    assert captured["key"] == f"users/pdf-owner/resumes/{record['resume_id']}/jobs/{record['job_id']}/optimizations/{optimization_id}/optimized.pdf"


def test_generate_s3_failure_is_safe(authenticated_user, monkeypatch):
    optimization_id = str(uuid4()); record = optimization_record(optimization_id)
    monkeypatch.setattr(route, "get_optimization_by_id", lambda *_: async_value(record)); monkeypatch.setattr(route, "get_job_by_id", lambda *_: async_value({"company": "Example", "role": "Engineer"})); monkeypatch.setattr(route, "generate_resume_pdf", lambda _: b"%PDF-" + b"x" * 1500)
    monkeypatch.setattr(route, "upload_file", lambda **_: (_ for _ in ()).throw(S3OperationError("secret")))
    response = client.post(f"/api/optimizations/{optimization_id}/generate-pdf")
    assert response.status_code == 503 and "secret" not in response.text


def test_pdf_access_uses_stored_metadata(authenticated_user, monkeypatch):
    optimization_id = str(uuid4()); record = optimization_record(optimization_id); record["generated_pdf"] = {"s3_key": "private/stored.pdf", "filename": "Test.pdf", "generated_at": datetime.now(timezone.utc)}; keys = []
    monkeypatch.setattr(route, "get_optimization_by_id", lambda *_: async_value(record))
    monkeypatch.setattr(route, "generate_presigned_url", lambda key, **_: keys.append(key) or "https://signed")
    response = client.get(f"/api/optimizations/{optimization_id}/pdf-access")
    assert response.status_code == 200 and keys == ["private/stored.pdf", "private/stored.pdf"]


def test_idor_returns_404(authenticated_user, monkeypatch):
    monkeypatch.setattr(route, "get_optimization_by_id", lambda *_: async_value(None))
    assert client.get(f"/api/optimizations/{uuid4()}").status_code == 404
    assert client.post(f"/api/optimizations/{uuid4()}/generate-pdf").status_code == 404
    assert client.delete(f"/api/optimizations/{uuid4()}").status_code == 404


async def async_value(value): return value
