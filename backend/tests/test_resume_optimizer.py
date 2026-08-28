import json
from types import SimpleNamespace
from uuid import UUID

import pytest

from app.config import settings
from app.services import mistral_service, resume_optimizer
from app.services.resume_matcher import calculate_resume_match
from tests.test_optimization_validator import ORIGINAL_BULLET, job_fixture, resume_fixture


def response(content: str) -> SimpleNamespace:
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


@pytest.fixture(autouse=True)
def clear_client_cache() -> None:
    mistral_service.get_mistral_client.cache_clear()
    yield
    mistral_service.get_mistral_client.cache_clear()


def test_mocked_mistral_generates_valid_safe_suggestion(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "suggestions": [
            {
                "section": "experience",
                "item_index": 0,
                "bullet_index": 0,
                "type": "rewrite_experience_bullet",
                "original": "Untrusted model original",
                "suggested": "Developed REST APIs using FastAPI for application backend workflows.",
                "reason": "Highlights existing REST API experience.",
                "matched_job_keywords": ["REST APIs"],
                "evidence": [ORIGINAL_BULLET],
            }
        ]
    }

    class FakeChat:
        def complete(self, **_: object) -> SimpleNamespace:
            return response(json.dumps(payload))

    class FakeMistral:
        def __init__(self, **_: object) -> None:
            self.chat = FakeChat()

    monkeypatch.setattr(settings, "mistral_api_key", "test-key")
    monkeypatch.setattr(mistral_service, "Mistral", FakeMistral)
    resume = resume_fixture()
    job = job_fixture()
    suggestions = resume_optimizer.generate_resume_suggestions(
        resume, job, calculate_resume_match(resume, job)
    )

    rewrites = [item for item in suggestions if item.type == "rewrite_experience_bullet"]
    assert len(rewrites) == 1
    UUID(rewrites[0].id)
    assert rewrites[0].original == ORIGINAL_BULLET
    assert rewrites[0].status == "pending"


def test_unsafe_model_suggestion_is_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "suggestions": [
            {
                "section": "experience",
                "item_index": 0,
                "bullet_index": 0,
                "type": "rewrite_experience_bullet",
                "suggested": "Deployed Docker services to AWS for 40% faster performance.",
                "reason": "Claims unsupported impact.",
                "matched_job_keywords": ["Docker", "AWS"],
                "evidence": [ORIGINAL_BULLET],
            }
        ]
    }

    class FakeChat:
        def complete(self, **_: object) -> SimpleNamespace:
            return response(json.dumps(payload))

    class FakeMistral:
        def __init__(self, **_: object) -> None:
            self.chat = FakeChat()

    monkeypatch.setattr(settings, "mistral_api_key", "test-key")
    monkeypatch.setattr(mistral_service, "Mistral", FakeMistral)
    resume = resume_fixture()
    job = job_fixture()
    suggestions = resume_optimizer.generate_resume_suggestions(
        resume, job, calculate_resume_match(resume, job)
    )
    assert all(item.type.startswith("confirm_") for item in suggestions)
    assert all("40%" not in item.suggested for item in suggestions)


def test_empty_first_response_retries_with_conservative_suggestion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    safe_payload = {
        "suggestions": [
            {
                "section": "experience",
                "item_index": 0,
                "bullet_index": 0,
                "type": "rewrite_experience_bullet",
                "suggested": "Developed REST APIs using FastAPI.",
                "reason": "Prioritizes relevant API work.",
                "matched_job_keywords": ["REST APIs"],
                "evidence": [ORIGINAL_BULLET],
            }
        ]
    }

    class FakeChat:
        calls = 0

        def complete(self, **_: object) -> SimpleNamespace:
            self.calls += 1
            payload = {"suggestions": []} if self.calls == 1 else safe_payload
            return response(json.dumps(payload))

    class FakeMistral:
        def __init__(self, **_: object) -> None:
            self.chat = FakeChat()

    monkeypatch.setattr(settings, "mistral_api_key", "test-key")
    monkeypatch.setattr(mistral_service, "Mistral", FakeMistral)
    resume = resume_fixture()
    job = job_fixture()

    suggestions = resume_optimizer.generate_resume_suggestions(
        resume, job, calculate_resume_match(resume, job)
    )

    rewrites = [item for item in suggestions if item.type == "rewrite_experience_bullet"]
    assert len(rewrites) == 1
    assert rewrites[0].status == "pending"


def test_model_can_propose_evidenced_skill_for_individual_approval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = "Built REST APIs using FastAPI and Docker."
    payload = {
        "suggestions": [
            {
                "section": "skills",
                "item_index": None,
                "bullet_index": None,
                "type": "add_technical_skill",
                "suggested": "Docker",
                "reason": "Surfaces an existing job-relevant skill.",
                "matched_job_keywords": ["Docker"],
                "evidence": [evidence],
            }
        ]
    }

    class FakeChat:
        def complete(self, **_: object) -> SimpleNamespace:
            return response(json.dumps(payload))

    class FakeMistral:
        def __init__(self, **_: object) -> None:
            self.chat = FakeChat()

    monkeypatch.setattr(settings, "mistral_api_key", "test-key")
    monkeypatch.setattr(mistral_service, "Mistral", FakeMistral)
    resume = resume_fixture(bullet=evidence)
    job = job_fixture()

    suggestions = resume_optimizer.generate_resume_suggestions(
        resume, job, calculate_resume_match(resume, job)
    )

    evidenced = [item for item in suggestions if item.type == "add_technical_skill"]
    assert len(evidenced) == 1
    assert evidenced[0].original == "Not listed in Technical Skills"


def test_missing_job_skill_becomes_explicit_confirmation_card(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeChat:
        def complete(self, **_: object) -> SimpleNamespace:
            return response(json.dumps({"suggestions": []}))

    class FakeMistral:
        def __init__(self, **_: object) -> None:
            self.chat = FakeChat()

    monkeypatch.setattr(settings, "mistral_api_key", "test-key")
    monkeypatch.setattr(mistral_service, "Mistral", FakeMistral)
    resume = resume_fixture()
    job = job_fixture()

    suggestions = resume_optimizer.generate_resume_suggestions(
        resume, job, calculate_resume_match(resume, job)
    )

    docker = next(item for item in suggestions if item.suggested == "Docker")
    assert docker.type == "confirm_technical_skill"
    assert docker.status == "pending"
    assert "confirmation required" in docker.original
