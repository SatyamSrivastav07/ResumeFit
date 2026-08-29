from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes import resumes as resumes_route
from app.schemas.auth import CurrentUser
from app.services.firebase_auth import get_current_user

client = TestClient(app)


@pytest.fixture
def authenticated_user() -> None:
    async def override_current_user() -> CurrentUser:
        return CurrentUser(uid="firebase-upload-user", email="user@example.com")

    app.dependency_overrides[get_current_user] = override_current_user
    yield
    app.dependency_overrides.clear()


def test_resume_upload_requires_authentication() -> None:
    response = client.post(
        "/api/resumes/upload",
        files={"file": ("resume.pdf", b"%PDF-1.4\ntest", "application/pdf")},
    )

    assert response.status_code == 401


def test_authenticated_valid_pdf_uploads_to_private_user_key(
    authenticated_user: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf_bytes = b"%PDF-1.4\n% harmless test PDF bytes"
    captured: dict[str, object] = {}

    def fake_upload_file(*, file_bytes: bytes, key: str, content_type: str) -> None:
        captured.update(
            file_bytes=file_bytes,
            key=key,
            content_type=content_type,
        )

    monkeypatch.setattr(resumes_route, "upload_file", fake_upload_file)

    response = client.post(
        "/api/resumes/upload",
        files={"file": ("my-resume.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 200
    body = response.json()
    UUID(body["resume_id"])
    assert body == {
        "resume_id": body["resume_id"],
        "filename": "my-resume.pdf",
        "size": len(pdf_bytes),
        "content_type": "application/pdf",
        "status": "uploaded",
    }
    assert captured == {
        "file_bytes": pdf_bytes,
        "key": (
            f"users/firebase-upload-user/resumes/{body['resume_id']}/original.pdf"
        ),
        "content_type": "application/pdf",
    }


def test_authenticated_non_pdf_is_rejected(
    authenticated_user: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload_called = False

    def fake_upload_file(**_: object) -> None:
        nonlocal upload_called
        upload_called = True

    monkeypatch.setattr(resumes_route, "upload_file", fake_upload_file)
    response = client.post(
        "/api/resumes/upload",
        files={"file": ("resume.txt", b"plain text", "text/plain")},
    )

    assert response.status_code == 400
    assert upload_called is False


def test_authenticated_excessive_filename_is_rejected(
    authenticated_user: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload_called = False

    def fake_upload_file(**_: object) -> None:
        nonlocal upload_called
        upload_called = True

    monkeypatch.setattr(resumes_route, "upload_file", fake_upload_file)
    response = client.post(
        "/api/resumes/upload",
        files={"file": (f"{'r' * 252}.pdf", b"%PDF-1.4\ntest", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded filename is too long."
    assert upload_called is False


def test_authenticated_pdf_with_invalid_header_is_rejected(
    authenticated_user: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload_called = False

    def fake_upload_file(**_: object) -> None:
        nonlocal upload_called
        upload_called = True

    monkeypatch.setattr(resumes_route, "upload_file", fake_upload_file)
    response = client.post(
        "/api/resumes/upload",
        files={"file": ("resume.pdf", b"not a real PDF", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded file is not a valid PDF."
    assert response.json()["error"]["code"] == "BAD_REQUEST"
    assert upload_called is False


def test_authenticated_pdf_over_five_mb_is_rejected(
    authenticated_user: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    upload_called = False

    def fake_upload_file(**_: object) -> None:
        nonlocal upload_called
        upload_called = True

    monkeypatch.setattr(resumes_route, "upload_file", fake_upload_file)
    oversized_pdf = b"%PDF-" + (b"x" * resumes_route.MAX_PDF_SIZE)
    response = client.post(
        "/api/resumes/upload",
        files={"file": ("large.pdf", oversized_pdf, "application/pdf")},
    )

    assert response.status_code == 413
    assert upload_called is False


def test_saved_resume_can_restore_secure_pdf_access(
    authenticated_user: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resume_id = str(uuid4())
    document = {
        "resume_id": resume_id,
        "original_filename": "saved-resume.pdf",
        "original_s3_key": f"users/firebase-upload-user/resumes/{resume_id}/original.pdf",
    }

    async def fake_get_resume(*_: object) -> dict[str, str]:
        return document

    def fake_presigned_url(key: str, **kwargs: object) -> str:
        disposition = str(kwargs["response_content_disposition"])
        mode = "preview" if disposition == "inline" else "download"
        return f"https://storage.example/{mode}?key={key}"

    monkeypatch.setattr(resumes_route, "get_resume_by_id", fake_get_resume)
    monkeypatch.setattr(resumes_route, "generate_presigned_url", fake_presigned_url)

    response = client.get(f"/api/resumes/{resume_id}/pdf-access")

    assert response.status_code == 200
    body = response.json()
    assert body["resume_id"] == resume_id
    assert body["filename"] == "saved-resume.pdf"
    assert body["status"] == "access_refreshed"
    assert body["preview_url"].startswith("https://storage.example/preview")
    assert body["download_url"].startswith("https://storage.example/download")
