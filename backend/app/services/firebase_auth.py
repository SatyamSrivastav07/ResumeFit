from pathlib import Path
from threading import Lock

import firebase_admin
from fastapi import Header, HTTPException, status
from firebase_admin import auth, credentials

from app.config import settings
from app.schemas.auth import CurrentUser

_initialization_lock = Lock()


class FirebaseConfigurationError(RuntimeError):
    """Raised when Firebase Admin cannot be initialized safely."""


def get_firebase_app() -> firebase_admin.App:
    """Return the process-wide Firebase Admin app, initializing it once."""

    try:
        return firebase_admin.get_app()
    except ValueError:
        pass

    with _initialization_lock:
        try:
            return firebase_admin.get_app()
        except ValueError:
            credentials_path = settings.firebase_credentials_path
            credentials_base64 = settings.firebase_credentials_base64
            if not credentials_path and not credentials_base64:
                raise FirebaseConfigurationError(
                    "Firebase Admin credentials are not configured."
                )

            try:
                if credentials_base64:
                    certificate = credentials.Certificate(
                        settings.firebase_credentials_from_base64()
                    )
                else:
                    resolved_path = Path(str(credentials_path)).expanduser().resolve()
                    if not resolved_path.is_file():
                        raise FirebaseConfigurationError(
                            "The configured Firebase Admin credentials file was not found."
                        )
                    certificate = credentials.Certificate(str(resolved_path))
                options = (
                    {"projectId": settings.firebase_project_id}
                    if settings.firebase_project_id
                    else None
                )
                return firebase_admin.initialize_app(certificate, options)
            except (ValueError, OSError) as exc:
                raise FirebaseConfigurationError(
                    "Firebase Admin credentials could not be loaded."
                ) from exc


def _unauthorized(detail: str = "Authentication credentials are invalid.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    """Verify a Firebase bearer token and return server-trusted identity claims."""

    if not authorization:
        raise _unauthorized("Authorization header is required.")

    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer":
        raise _unauthorized("Authorization must use the Bearer scheme.")

    token = token.strip()
    if not token:
        raise _unauthorized("Bearer token is required.")

    try:
        firebase_app = get_firebase_app()
    except FirebaseConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not configured.",
        ) from exc

    try:
        # Revocation checks matter after password resets, account deletion, and
        # explicit administrator session revocation. Firebase disables this
        # network-backed check by default, so opt in for protected API access.
        decoded_token = auth.verify_id_token(
            token,
            app=firebase_app,
            check_revoked=True,
        )
    except (
        auth.ExpiredIdTokenError,
        auth.InvalidIdTokenError,
        auth.RevokedIdTokenError,
        auth.CertificateFetchError,
        ValueError,
    ) as exc:
        raise _unauthorized() from exc

    uid = decoded_token.get("uid") or decoded_token.get("sub")
    if not uid:
        raise _unauthorized()

    return CurrentUser(uid=uid, email=decoded_token.get("email"))
