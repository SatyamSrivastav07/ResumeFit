import re
from dataclasses import dataclass

from app.schemas.job import JobAnalysisSchema
from app.schemas.match import MatchAnalysisSchema
from app.schemas.optimization import OptimizationSuggestion
from app.schemas.resume import ResumeSchema
from app.services.resume_matcher import (
    calculate_resume_match,
    normalize_skill,
    phrase_in_text,
)

KNOWN_TECHNOLOGIES = {
    "python", "java", "javascript", "typescript", "c", "cpp", "csharp", "go", "rust", "ruby", "php", "swift", "kotlin",
    "react", "reactnative", "angular", "vue", "nodejs", "express", "fastapi", "django", "flask", "spring", "dotnet",
    "postgresql", "mysql", "mongodb", "redis", "sqlite", "oracle", "dynamodb",
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "jenkins", "githubactions", "cicd",
    "git", "linux", "restapi", "graphql", "html", "css", "tailwind", "firebase",
    "dsa", "rag", "mern",
}
NUMBER_PATTERN = re.compile(r"(?<!\w)\d+(?:[.,]\d+)?%?(?!\w)")
HIGH_RISK_CLAIM_VERBS = {
    "led", "managed", "mentored", "deployed", "architected", "owned",
    "increased", "reduced", "saved",
}
TECHNICAL_SKILL_MARKER = "Not listed in Technical Skills"
TOOL_SKILL_MARKER = "Not listed in Tools"
SKILL_SUGGESTION_TYPES = {"add_technical_skill", "add_tool_skill"}
CONFIRM_SKILL_SUGGESTION_TYPES = {"confirm_technical_skill", "confirm_tool_skill"}
ALL_SKILL_SUGGESTION_TYPES = SKILL_SUGGESTION_TYPES | CONFIRM_SKILL_SUGGESTION_TYPES
CONFIRM_TECHNICAL_SKILL_MARKER = "Not found in uploaded resume — confirmation required"
CONFIRM_TOOL_SKILL_MARKER = "Not found in uploaded resume tools — confirmation required"


class UnsafeSuggestionError(ValueError):
    """Raised when a suggestion cannot be grounded in the supplied resume."""


class UnsafeSuggestionsError(ValueError):
    def __init__(self, suggestion_ids: list[str]) -> None:
        self.suggestion_ids = suggestion_ids
        super().__init__("One or more suggestions introduce unsupported resume information.")


@dataclass(frozen=True)
class AppliedOptimization:
    optimized_resume: ResumeSchema
    before_match: MatchAnalysisSchema
    after_match: MatchAnalysisSchema


def _normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())


def resume_source_texts(resume: ResumeSchema) -> list[str]:
    values: list[str] = []
    if resume.summary:
        values.append(resume.summary)
    values.extend(resume.skills.technical)
    values.extend(resume.skills.tools)
    values.extend(resume.skills.soft)
    for item in resume.experience:
        values.extend([item.company, item.role])
        values.extend(value for value in (item.location, item.start_date, item.end_date) if value)
        values.extend(item.description)
    for project in resume.projects:
        values.append(project.name)
        values.extend(project.technologies)
        values.extend(project.description)
    for item in resume.education:
        values.extend(
            value
            for value in (
                item.institution,
                item.degree,
                item.field,
                item.location,
                item.start_date,
                item.end_date,
                item.score,
            )
            if value
        )
    values.extend(resume.certifications)
    values.extend(resume.achievements)
    values.extend(resume.languages)
    return values


def get_target_text(resume: ResumeSchema, suggestion: OptimizationSuggestion) -> str:
    if suggestion.type == "add_technical_skill":
        return TECHNICAL_SKILL_MARKER
    if suggestion.type == "add_tool_skill":
        return TOOL_SKILL_MARKER
    if suggestion.type == "confirm_technical_skill":
        return CONFIRM_TECHNICAL_SKILL_MARKER
    if suggestion.type == "confirm_tool_skill":
        return CONFIRM_TOOL_SKILL_MARKER
    if suggestion.type == "rewrite_summary":
        if not resume.summary:
            raise UnsafeSuggestionError("A missing summary cannot be rewritten.")
        return resume.summary

    if suggestion.item_index is None or suggestion.bullet_index is None:
        raise UnsafeSuggestionError("The suggestion target is incomplete.")
    try:
        if suggestion.type == "rewrite_experience_bullet":
            return resume.experience[suggestion.item_index].description[suggestion.bullet_index]
        if suggestion.type == "rewrite_project_bullet":
            return resume.projects[suggestion.item_index].description[suggestion.bullet_index]
    except IndexError as exc:
        raise UnsafeSuggestionError("The suggestion target does not exist.") from exc
    raise UnsafeSuggestionError("Unsupported optimization operation.")


def _supported_technologies(resume: ResumeSchema) -> set[str]:
    explicit = [
        *resume.skills.technical,
        *resume.skills.tools,
        *(technology for project in resume.projects for technology in project.technologies),
    ]
    supported = {normalize_skill(value) for value in explicit}
    professional_text = "\n".join(resume_source_texts(resume))
    supported.update(
        technology
        for technology in KNOWN_TECHNOLOGIES
        if phrase_in_text(technology, professional_text)
    )
    return {value for value in supported if value}


def _mentioned_technologies(text: str) -> set[str]:
    return {
        technology
        for technology in KNOWN_TECHNOLOGIES
        if phrase_in_text(technology, text)
    }


def validate_evidence(resume: ResumeSchema, suggestion: OptimizationSuggestion) -> None:
    if suggestion.type in CONFIRM_SKILL_SUGGESTION_TYPES:
        return
    sources = [_normalize_text(value) for value in resume_source_texts(resume)]
    for evidence in suggestion.evidence:
        normalized = _normalize_text(evidence)
        if not normalized or not any(normalized in source for source in sources):
            raise UnsafeSuggestionError("Suggestion evidence is not present in the resume.")


def validate_new_technologies(resume: ResumeSchema, suggestion: OptimizationSuggestion) -> None:
    if suggestion.type in CONFIRM_SKILL_SUGGESTION_TYPES:
        return
    unsupported = _mentioned_technologies(suggestion.suggested) - _supported_technologies(resume)
    if unsupported:
        raise UnsafeSuggestionError("Suggestion introduces an unsupported technology.")


def validate_metrics(suggestion: OptimizationSuggestion) -> None:
    source_text = "\n".join([suggestion.original, *suggestion.evidence])
    source_numbers = set(NUMBER_PATTERN.findall(source_text))
    suggested_numbers = set(NUMBER_PATTERN.findall(suggestion.suggested))
    if suggested_numbers - source_numbers:
        raise UnsafeSuggestionError("Suggestion introduces an unsupported numerical claim.")


def validate_high_risk_claims(suggestion: OptimizationSuggestion) -> None:
    source_tokens = set(re.findall(r"[a-z0-9]+", "\n".join([suggestion.original, *suggestion.evidence]).casefold()))
    suggested_tokens = set(re.findall(r"[a-z0-9]+", suggestion.suggested.casefold()))
    if (suggested_tokens & HIGH_RISK_CLAIM_VERBS) - source_tokens:
        raise UnsafeSuggestionError(
            "Suggestion introduces an unsupported responsibility or impact claim."
        )


def validate_skill_addition(resume: ResumeSchema, suggestion: OptimizationSuggestion) -> None:
    if suggestion.type not in ALL_SKILL_SUGGESTION_TYPES:
        return
    skill = suggestion.suggested.strip()
    if len(skill) > 80 or any(character in skill for character in ("\n", ",", ";")):
        raise UnsafeSuggestionError("Skill suggestions must contain one concise skill name.")
    destination = (
        resume.skills.technical
        if suggestion.type in {"add_technical_skill", "confirm_technical_skill"}
        else resume.skills.tools
    )
    if normalize_skill(skill) in {normalize_skill(value) for value in destination}:
        raise UnsafeSuggestionError("Suggested skill is already listed in that section.")
    if (
        suggestion.type not in CONFIRM_SKILL_SUGGESTION_TYPES
        and not any(phrase_in_text(skill, evidence) for evidence in suggestion.evidence)
    ):
        raise UnsafeSuggestionError(
            "Suggested skill is not supported by the cited resume evidence."
        )


def validate_suggestion(resume: ResumeSchema, suggestion: OptimizationSuggestion) -> None:
    target = get_target_text(resume, suggestion)
    if _normalize_text(suggestion.original) != _normalize_text(target):
        raise UnsafeSuggestionError("Suggestion original text does not match its target.")
    validate_evidence(resume, suggestion)
    validate_new_technologies(resume, suggestion)
    validate_metrics(suggestion)
    validate_high_risk_claims(suggestion)
    validate_skill_addition(resume, suggestion)


def suggestion_target_key(
    suggestion: OptimizationSuggestion,
) -> tuple[str, int | None, int | None, str]:
    skill = (
        normalize_skill(suggestion.suggested)
        if suggestion.type in ALL_SKILL_SUGGESTION_TYPES
        else ""
    )
    return (suggestion.type, suggestion.item_index, suggestion.bullet_index, skill)


def apply_approved_suggestions(
    resume: ResumeSchema,
    job: JobAnalysisSchema,
    suggestions: list[OptimizationSuggestion],
) -> AppliedOptimization:
    approved = [item for item in suggestions if item.status in {"accepted", "edited"}]
    invalid_ids: list[str] = []
    seen_targets: set[tuple[str, int | None, int | None, str]] = set()
    for suggestion in approved:
        target_key = suggestion_target_key(suggestion)
        if target_key in seen_targets:
            invalid_ids.append(suggestion.id)
            continue
        seen_targets.add(target_key)
        try:
            validate_suggestion(resume, suggestion)
        except UnsafeSuggestionError:
            invalid_ids.append(suggestion.id)
    if invalid_ids:
        raise UnsafeSuggestionsError(invalid_ids)

    optimized = resume.model_copy(deep=True)
    for suggestion in approved:
        if suggestion.type == "rewrite_summary":
            optimized.summary = suggestion.suggested
        elif suggestion.type == "rewrite_experience_bullet":
            optimized.experience[suggestion.item_index].description[suggestion.bullet_index] = suggestion.suggested
        elif suggestion.type == "rewrite_project_bullet":
            optimized.projects[suggestion.item_index].description[suggestion.bullet_index] = suggestion.suggested
        elif suggestion.type in {"add_technical_skill", "confirm_technical_skill"}:
            optimized.skills.technical.append(suggestion.suggested)
        elif suggestion.type in {"add_tool_skill", "confirm_tool_skill"}:
            optimized.skills.tools.append(suggestion.suggested)

    # Revalidate after list mutation so additions are deduplicated and obvious
    # technologies/tools land in the correct ATS section.
    optimized = ResumeSchema.model_validate(optimized.model_dump())

    return AppliedOptimization(
        optimized_resume=optimized,
        before_match=calculate_resume_match(resume, job),
        after_match=calculate_resume_match(optimized, job),
    )
