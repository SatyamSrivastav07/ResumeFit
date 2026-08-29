class ApplicationError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"
    public_message = "An unexpected error occurred."

    def __init__(self, message: str | None = None, *, headers: dict[str, str] | None = None) -> None:
        super().__init__(message or self.public_message)
        self.message = message or self.public_message
        self.headers = headers or {}


class ResourceNotFoundError(ApplicationError):
    status_code = 404
    code = "RESOURCE_NOT_FOUND"
    public_message = "The requested resource was not found."


class DatabaseUnavailableError(ApplicationError):
    status_code = 503
    code = "DATABASE_UNAVAILABLE"
    public_message = "Database is temporarily unavailable. Please try again."


class AIServiceError(ApplicationError):
    status_code = 502
    code = "AI_SERVICE_UNAVAILABLE"
    public_message = "AI analysis is temporarily unavailable. Please try again."


class StorageError(ApplicationError):
    status_code = 503
    code = "STORAGE_UNAVAILABLE"
    public_message = "File storage is temporarily unavailable. Please try again."


class RateLimitError(ApplicationError):
    status_code = 429
    code = "RATE_LIMIT_EXCEEDED"
    public_message = "Too many requests. Please try again shortly."
