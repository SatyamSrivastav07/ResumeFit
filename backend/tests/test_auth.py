from fastapi.testclient import TestClient

from app.main import app
from app.schemas.auth import CurrentUser
from app.services.firebase_auth import get_current_user

client = TestClient(app)


def test_auth_me_requires_authorization_header() -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json()["detail"] == "Authorization header is required."
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_auth_me_rejects_invalid_scheme() -> None:
    response = client.get("/api/auth/me", headers={"Authorization": "Basic abc123"})

    assert response.status_code == 401


def test_auth_me_returns_verified_dependency_identity() -> None:
    async def override_current_user() -> CurrentUser:
        return CurrentUser(uid="firebase-test-uid", email="user@example.com")

    app.dependency_overrides[get_current_user] = override_current_user
    try:
        response = client.get("/api/auth/me")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "uid": "firebase-test-uid",
        "email": "user@example.com",
    }


def test_auth_me_checks_token_revocation(monkeypatch) -> None:
    firebase_app = object()
    observed: dict[str, object] = {}

    monkeypatch.setattr(
        "app.services.firebase_auth.get_firebase_app",
        lambda: firebase_app,
    )

    def verify_id_token(token: str, *, app: object, check_revoked: bool):
        observed.update(
            token=token,
            app=app,
            check_revoked=check_revoked,
        )
        return {"uid": "firebase-test-uid", "email": "user@example.com"}

    monkeypatch.setattr(
        "app.services.firebase_auth.auth.verify_id_token",
        verify_id_token,
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer valid-token"},
    )

    assert response.status_code == 200
    assert observed == {
        "token": "valid-token",
        "app": firebase_app,
        "check_revoked": True,
    }
