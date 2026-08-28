import re
import unicodedata


_UNSAFE_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f\x7f]+')
_NON_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
_REPEATED_UNDERSCORES = re.compile(r"_+")


def sanitize_filename_part(value: str | None, *, fallback: str = "Resume", max_length: int = 60) -> str:
    """Return a short ASCII filename component safe for Content-Disposition."""

    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = _UNSAFE_FILENAME_CHARS.sub(" ", ascii_value)
    cleaned = _NON_FILENAME_CHARS.sub("_", cleaned.strip())
    cleaned = _REPEATED_UNDERSCORES.sub("_", cleaned).strip("._-")
    cleaned = cleaned[:max_length].rstrip("._-")
    return cleaned or fallback


def build_resume_filename(candidate_name: str | None, company: str, role: str) -> str:
    parts = [
        sanitize_filename_part(candidate_name, fallback="Resume"),
        sanitize_filename_part(company, fallback="Company"),
        sanitize_filename_part(role, fallback="Role"),
    ]
    return f"{'_'.join(parts)[:180].rstrip('._-')}.pdf"
