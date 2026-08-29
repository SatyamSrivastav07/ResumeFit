import hashlib
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Depends, Request

from app.config import settings
from app.core.exceptions import RateLimitError
from app.schemas.auth import CurrentUser
from app.services.firebase_auth import get_current_user


class InMemoryRateLimiter:
    """Process-local limiter; use a shared gateway/Redis limiter for multi-instance deployments."""

    def __init__(self) -> None:
        self._events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, category: str, identity: str, limit: int, window_seconds: int) -> int | None:
        now = time.monotonic()
        threshold = now - window_seconds
        key = (category, identity)
        with self._lock:
            events = self._events[key]
            while events and events[0] <= threshold:
                events.popleft()
            if len(events) >= limit:
                return max(1, int(window_seconds - (now - events[0])))
            events.append(now)
        return None

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


limiter = InMemoryRateLimiter()


def _user_reference(uid: str) -> str:
    return hashlib.sha256(uid.encode("utf-8")).hexdigest()[:16]


class RateLimitDependency:
    def __init__(self, category: str, setting_name: str) -> None:
        self.category = category
        self.setting_name = setting_name

    async def __call__(
        self,
        request: Request,
        current_user: CurrentUser = Depends(get_current_user),
    ) -> None:
        identity = _user_reference(current_user.uid)
        request.state.user_ref = identity
        retry_after = limiter.check(
            self.category,
            identity,
            int(getattr(settings, self.setting_name)),
            settings.rate_limit_window_seconds,
        )
        if retry_after is not None:
            raise RateLimitError(headers={"Retry-After": str(retry_after)})


authenticated_rate_limit = RateLimitDependency("authenticated", "rate_limit_authenticated")
ai_rate_limit = RateLimitDependency("ai", "rate_limit_ai")
upload_rate_limit = RateLimitDependency("upload", "rate_limit_upload")
pdf_rate_limit = RateLimitDependency("pdf", "rate_limit_pdf")
