from app.utils.filenames import build_resume_filename, sanitize_filename_part


def test_sanitize_filename_part_removes_unsafe_characters() -> None:
    assert sanitize_filename_part(' Software Engineer / Backend:*?"<>| ') == "Software_Engineer_Backend"


def test_sanitize_filename_part_normalizes_unicode_and_limits_length() -> None:
    assert sanitize_filename_part("Satyám Śrivastav") == "Satyam_Srivastav"
    assert len(sanitize_filename_part("a" * 100, max_length=25)) == 25


def test_build_resume_filename_has_safe_fallbacks() -> None:
    filename = build_resume_filename(None, "", "Backend / Engineer")
    assert filename == "Resume_Company_Backend_Engineer.pdf"
    assert not any(character in filename for character in '\\/:*?"<>|')
