from fastapi.testclient import TestClient

from app.main import app
from app.schemas.auth import CurrentUser
from app.services.firebase_auth import get_current_user

client = TestClient(app)


def test_auth_me_requires_authorization_header() -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"detail": "Authorization header is required."}


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
