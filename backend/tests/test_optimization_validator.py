from uuid import uuid4

import pytest

from app.schemas.job import JobAnalysisSchema
from app.schemas.optimization import OptimizationSuggestion
from app.schemas.resume import ResumeSchema
from app.services.optimization_validator import (
    UnsafeSuggestionError,
    UnsafeSuggestionsError,
    apply_approved_suggestions,
    validate_suggestion,
)

ORIGINAL_BULLET = "Built REST APIs using FastAPI."


def resume_fixture(*, bullet: str = ORIGINAL_BULLET, technologies: list[str] | None = None) -> ResumeSchema:
    return ResumeSchema.model_validate(
        {
            "personal_info": {"name": "Candidate", "email": "candidate@example.com"},
            "summary": "Backend engineer building reliable APIs.",
            "skills": {"technical": technologies or ["Python", "FastAPI"], "tools": ["Git"], "soft": []},
            "experience": [
                {
                    "company": "Example Corp",
                    "role": "Software Engineer",
                    "description": [bullet],
                }
            ],
            "projects": [],
            "education": [],
        }
    )


def job_fixture() -> JobAnalysisSchema:
    return JobAnalysisSchema.model_validate(
        {
            "company": "Target Corp",
            "role": "Backend Engineer",
            "required_skills": ["Python", "FastAPI", "REST APIs"],
            "preferred_skills": ["Docker", "AWS"],
            "responsibilities": ["Build application backend workflows"],
            "important_keywords": ["REST APIs", "backend workflows"],
        }
    )


def suggestion(
    *,
    original: str = ORIGINAL_BULLET,
    suggested: str = "Developed REST APIs using FastAPI for application backend workflows.",
    evidence: list[str] | None = None,
    status: str = "pending",
) -> OptimizationSuggestion:
    return OptimizationSuggestion.model_validate(
        {
            "id": str(uuid4()),
            "section": "experience",
            "item_index": 0,
            "bullet_index": 0,
            "type": "rewrite_experience_bullet",
            "original": original,
            "suggested": suggested,
            "reason": "Highlights existing API work.",
            "matched_job_keywords": ["REST APIs"],
            "evidence": evidence or [ORIGINAL_BULLET],
            "status": status,
        }
    )


def test_valid_grounded_rewrite_is_allowed() -> None:
    validate_suggestion(resume_fixture(), suggestion())


def test_unsupported_technology_is_rejected() -> None:
    unsafe = suggestion(suggested="Built a Dockerized React application deployed to AWS.")
    with pytest.raises(UnsafeSuggestionError, match="technology"):
        validate_suggestion(resume_fixture(technologies=["React"]), unsafe)


def test_unsupported_metric_is_rejected() -> None:
    original = "Improved application performance."
    unsafe = suggestion(
        original=original,
        suggested="Improved application performance by 40%.",
        evidence=[original],
    )
    with pytest.raises(UnsafeSuggestionError, match="numerical"):
        validate_suggestion(resume_fixture(bullet=original), unsafe)


def test_preserved_metric_is_allowed() -> None:
    original = "Reduced page load time by 30%."
    safe = suggestion(
        original=original,
        suggested="Reduced page load time by 30% through frontend optimization.",
        evidence=[original],
    )
    validate_suggestion(resume_fixture(bullet=original), safe)


def test_immutable_company_value_cannot_be_targeted_as_a_bullet() -> None:
    unsafe = suggestion(original="Example Corp", evidence=["Example Corp"])
    with pytest.raises(UnsafeSuggestionError, match="does not match"):
        validate_suggestion(resume_fixture(), unsafe)


def test_accepted_rewrite_changes_only_copy_and_preserves_original() -> None:
    resume = resume_fixture()
    accepted = suggestion(status="accepted")
    applied = apply_approved_suggestions(resume, job_fixture(), [accepted])

    assert applied.optimized_resume.experience[0].description[0] == accepted.suggested
    assert applied.optimized_resume.experience[0].company == "Example Corp"
    assert resume.experience[0].description[0] == ORIGINAL_BULLET


@pytest.mark.parametrize("status", ["rejected", "pending"])
def test_rejected_or_pending_suggestion_is_not_applied(status: str) -> None:
    resume = resume_fixture()
    applied = apply_approved_suggestions(resume, job_fixture(), [suggestion(status=status)])
    assert applied.optimized_resume == resume


def test_unsafe_edited_suggestion_is_rejected_server_side() -> None:
    edited = suggestion(suggested="Deployed backend services to AWS.", status="edited")
    with pytest.raises(UnsafeSuggestionsError) as error:
        apply_approved_suggestions(resume_fixture(), job_fixture(), [edited])
    assert error.value.suggestion_ids == [edited.id]


def skill_suggestion(*, skill: str, evidence: str, status: str = "pending") -> OptimizationSuggestion:
    return OptimizationSuggestion.model_validate(
        {
            "id": str(uuid4()),
            "section": "skills",
            "item_index": None,
            "bullet_index": None,
            "type": "add_technical_skill",
            "original": "Not listed in Technical Skills",
            "suggested": skill,
            "reason": "Surfaces an existing JD-relevant skill.",
            "matched_job_keywords": [skill],
            "evidence": [evidence],
            "status": status,
        }
    )


def test_evidenced_skill_addition_is_applied_only_after_approval() -> None:
    evidence = "Built and containerized REST APIs using FastAPI and Docker."
    resume = resume_fixture(bullet=evidence)
    proposed = skill_suggestion(skill="Docker", evidence=evidence, status="accepted")

    validate_suggestion(resume, proposed)
    applied = apply_approved_suggestions(resume, job_fixture(), [proposed])

    assert "Docker" in applied.optimized_resume.skills.technical
    assert "Docker" not in resume.skills.technical


def test_skill_addition_without_resume_evidence_is_rejected() -> None:
    proposed = skill_suggestion(skill="Kubernetes", evidence=ORIGINAL_BULLET)

    with pytest.raises(UnsafeSuggestionError, match="unsupported"):
        validate_suggestion(resume_fixture(), proposed)


def test_confirmed_missing_skill_is_added_only_after_user_acceptance() -> None:
    confirmed = OptimizationSuggestion.model_validate(
        {
            "id": str(uuid4()),
            "section": "skills",
            "type": "confirm_tool_skill",
            "original": "Not found in uploaded resume tools — confirmation required",
            "suggested": "Jupyter Notebook",
            "reason": "The job requests it; accept only if genuinely known.",
            "matched_job_keywords": ["Jupyter Notebook"],
            "evidence": [
                "Candidate confirmation required because this skill was not found in the uploaded resume."
            ],
            "status": "accepted",
        }
    )

    applied = apply_approved_suggestions(resume_fixture(), job_fixture(), [confirmed])

    assert "Jupyter Notebook" in applied.optimized_resume.skills.tools
