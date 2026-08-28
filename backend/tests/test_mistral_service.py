import json
from types import SimpleNamespace

import pytest

from app.config import settings
from app.services import mistral_service


VALID_RESUME = {
    "personal_info": {"name": "Satyam Srivastav"},
    "summary": None,
    "skills": {"technical": ["Python"], "tools": [], "soft": []},
    "experience": [],
    "projects": [],
    "education": [],
    "certifications": [],
    "achievements": [],
    "languages": [],
}

VALID_JOB_ANALYSIS = {
    "company": "Hallucinated Company",
    "role": "Hallucinated Role",
    "experience_level": "Entry Level",
    "employment_type": "Full-time",
    "required_skills": ["Python", "REST APIs"],
    "preferred_skills": ["Docker"],
    "programming_languages": ["Python"],
    "frameworks": [],
    "databases": ["PostgreSQL"],
    "cloud_and_devops": ["Docker"],
    "tools": ["Git"],
    "soft_skills": ["Communication"],
    "responsibilities": ["Build and maintain backend services"],
    "education_requirements": [],
    "experience_requirements": ["0-2 years of experience"],
    "important_keywords": ["REST APIs", "backend development"],
    "domain_keywords": [],
}


def _response(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


@pytest.fixture(autouse=True)
def clear_mistral_client_cache() -> None:
    mistral_service.get_mistral_client.cache_clear()
    yield
    mistral_service.get_mistral_client.cache_clear()


def test_mistral_json_response_is_validated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeComplete:
        def complete(self, **_: object) -> SimpleNamespace:
            return _response(json.dumps(VALID_RESUME))

    class FakeMistral:
        def __init__(self, **_: object) -> None:
            self.chat = FakeComplete()

    monkeypatch.setattr(settings, "mistral_api_key", "test-key")
    monkeypatch.setattr(mistral_service, "Mistral", FakeMistral)

    result = mistral_service.parse_resume_text("Resume text with enough details")
    assert result.personal_info.name == "Satyam Srivastav"
    assert result.skills.technical == ["Python"]


def test_invalid_first_response_is_retried_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    class FakeComplete:
        def complete(self, **_: object) -> SimpleNamespace:
            nonlocal calls
            calls += 1
            if calls == 1:
                return _response("not json")
            return _response(json.dumps(VALID_RESUME))

    class FakeMistral:
        def __init__(self, **_: object) -> None:
            self.chat = FakeComplete()

    monkeypatch.setattr(settings, "mistral_api_key", "test-key")
    monkeypatch.setattr(mistral_service, "Mistral", FakeMistral)

    result = mistral_service.parse_resume_text("Resume text")
    assert result.personal_info.name == "Satyam Srivastav"
    assert calls == 2


def test_job_analysis_is_validated_and_preserves_user_company_and_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeComplete:
        def complete(self, **_: object) -> SimpleNamespace:
            return _response(json.dumps(VALID_JOB_ANALYSIS))

    class FakeMistral:
        def __init__(self, **_: object) -> None:
            self.chat = FakeComplete()

    monkeypatch.setattr(settings, "mistral_api_key", "test-key")
    monkeypatch.setattr(mistral_service, "Mistral", FakeMistral)

    result = mistral_service.analyze_job_description(
        company="Example Corp",
        role="Software Engineer",
        job_description="A valid job description with explicit requirements.",
    )

    assert result.company == "Example Corp"
    assert result.role == "Software Engineer"
    assert result.required_skills == ["Python", "REST APIs"]


def test_invalid_job_analysis_response_is_retried_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    class FakeComplete:
        def complete(self, **_: object) -> SimpleNamespace:
            nonlocal calls
            calls += 1
            return _response("not json" if calls == 1 else json.dumps(VALID_JOB_ANALYSIS))

    class FakeMistral:
        def __init__(self, **_: object) -> None:
            self.chat = FakeComplete()

    monkeypatch.setattr(settings, "mistral_api_key", "test-key")
    monkeypatch.setattr(mistral_service, "Mistral", FakeMistral)

    result = mistral_service.analyze_job_description(
        company="Example Corp",
        role="Software Engineer",
        job_description="A valid job description with explicit requirements.",
    )
    assert result.company == "Example Corp"
    assert calls == 2
