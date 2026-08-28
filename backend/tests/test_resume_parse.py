from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes import resumes as resumes_route
from app.schemas.auth import CurrentUser
from app.schemas.resume import ResumeSchema
from app.services.firebase_auth import get_current_user
from app.services.mistral_service import MistralServiceError
from app.services.pdf_parser import PDFParseError, UnreadablePDFError
from app.services.s3_service import S3ObjectNotFoundError

client = TestClient(app)


@pytest.fixture
def authenticated_user() -> None:
    async def override_current_user() -> CurrentUser:
        return CurrentUser(uid="firebase-parse-user", email="user@example.com")

    app.dependency_overrides[get_current_user] = override_current_user
    yield
    app.dependency_overrides.clear()


def test_parse_requires_authentication() -> None:
    response = client.post(f"/api/resumes/{uuid4()}/parse")
    assert response.status_code == 401


def test_invalid_resume_id_returns_400(authenticated_user: None) -> None:
    response = client.post("/api/resumes/not-a-uuid/parse")
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid resume ID."}


def test_missing_s3_resume_returns_404(
    authenticated_user: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing(_: str) -> bytes:
        raise S3ObjectNotFoundError("missing")

    monkeypatch.setattr(resumes_route, "download_file", missing)
    response = client.post(f"/api/resumes/{uuid4()}/parse")
    assert response.status_code == 404
    assert response.json() == {"detail": "Resume was not found."}


def test_valid_resume_returns_structured_data(
    authenticated_user: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resume_id = str(uuid4())
    captured: dict[str, str] = {}

    def download(key: str) -> bytes:
        captured["key"] = key
        return b"pdf-bytes"

    monkeypatch.setattr(resumes_route, "download_file", download)
    monkeypatch.setattr(resumes_route, "get_resume_by_id", lambda *_: _async_value({"status": "uploaded", "original_s3_key": f"users/firebase-parse-user/resumes/{resume_id}/original.pdf"}))
    monkeypatch.setattr(resumes_route, "update_parsed_resume", lambda *_: _async_value(True))
    monkeypatch.setattr(
        resumes_route,
        "extract_text_from_pdf",
        lambda _: "Satyam Srivastav Software Engineer Python FastAPI AWS experience",
    )
    monkeypatch.setattr(
        resumes_route,
        "parse_resume_text",
        lambda _: ResumeSchema.model_validate(
            {
                "personal_info": {"name": "Satyam Srivastav", "email": "satyam@example.com"},
                "summary": "Software engineer",
                "skills": {"technical": ["Python", "FastAPI"]},
                "experience": [],
                "projects": [],
                "education": [],
            }
        ),
    )

    response = client.post(f"/api/resumes/{resume_id}/parse")

    assert response.status_code == 200
    body = response.json()
    assert body["resume_id"] == resume_id
    assert body["status"] == "parsed"
    assert body["resume"]["personal_info"]["name"] == "Satyam Srivastav"
    assert "raw_text" not in body
    assert captured["key"] == f"users/firebase-parse-user/resumes/{resume_id}/original.pdf"


@pytest.mark.parametrize(
    "parser_error",
    [PDFParseError("The PDF is corrupt or unreadable."), UnreadablePDFError("The PDF does not contain enough selectable text.")],
)
def test_unreadable_pdf_returns_422(
    authenticated_user: None,
    monkeypatch: pytest.MonkeyPatch,
    parser_error: PDFParseError,
) -> None:
    monkeypatch.setattr(resumes_route, "download_file", lambda _: b"pdf-bytes")
    monkeypatch.setattr(resumes_route, "get_resume_by_id", lambda *args: _async_value({"status": "uploaded", "original_s3_key": f"users/firebase-parse-user/resumes/{args[-1]}/original.pdf"}))
    monkeypatch.setattr(resumes_route, "mark_parse_failed", lambda *_: _async_value(None))

    def fail_extract(_: bytes) -> str:
        raise parser_error

    monkeypatch.setattr(resumes_route, "extract_text_from_pdf", fail_extract)
    response = client.post(f"/api/resumes/{uuid4()}/parse")
    assert response.status_code == 422


def test_mistral_failure_returns_safe_502(
    authenticated_user: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(resumes_route, "download_file", lambda _: b"pdf-bytes")
    monkeypatch.setattr(resumes_route, "get_resume_by_id", lambda *args: _async_value({"status": "uploaded", "original_s3_key": f"users/firebase-parse-user/resumes/{args[-1]}/original.pdf"}))
    monkeypatch.setattr(resumes_route, "mark_parse_failed", lambda *_: _async_value(None))
    monkeypatch.setattr(resumes_route, "extract_text_from_pdf", lambda _: "x" * 100)

    def fail_mistral(_: str) -> ResumeSchema:
        raise MistralServiceError("secret provider details")

    monkeypatch.setattr(resumes_route, "parse_resume_text", fail_mistral)
    response = client.post(f"/api/resumes/{uuid4()}/parse")
    assert response.status_code == 502
    assert response.json() == {
        "detail": "Unable to parse this resume right now. Please try again."
    }
    assert "secret provider details" not in response.text


async def _async_value(value):
    return value
