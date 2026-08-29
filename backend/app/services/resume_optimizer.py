import json
import logging
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.config import settings
from app.prompts.resume_optimizer import SYSTEM_PROMPT, build_optimizer_prompt
from app.schemas.job import JobAnalysisSchema
from app.schemas.match import MatchAnalysisSchema
from app.schemas.optimization import OptimizationSuggestion, SuggestionType
from app.schemas.resume import ResumeSchema, classify_skill_category
from app.services.mistral_service import (
    MistralResponseError,
    MistralServiceError,
    _message_content,
    get_mistral_client,
)
from app.services.optimization_validator import (
    UnsafeSuggestionError,
    get_target_text,
    suggestion_target_key,
    validate_suggestion,
)
from app.services.resume_matcher import normalize_skill

logger = logging.getLogger(__name__)
MAX_OPTIMIZATION_SUGGESTIONS = 20
MAX_SKILL_CONFIRMATIONS = 12
MIN_USEFUL_SUGGESTIONS = 3
CONFIRMATION_EVIDENCE = (
    "Candidate confirmation required because this skill was not found in the uploaded resume."
)


def _normalized_skill_suggestion_type(
    suggestion_type: SuggestionType,
    skill: str,
) -> SuggestionType:
    category = classify_skill_category(skill)
    if category is None or suggestion_type not in {
        "add_technical_skill", "add_tool_skill",
        "confirm_technical_skill", "confirm_tool_skill",
    }:
        return suggestion_type
    prefix = "confirm" if suggestion_type.startswith("confirm_") else "add"
    return f"{prefix}_{'tool' if category == 'tools' else 'technical'}_skill"


class DraftModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OptimizationSuggestionDraft(DraftModel):
    section: str
    item_index: int | None = Field(default=None, ge=0)
    bullet_index: int | None = Field(default=None, ge=0)
    type: SuggestionType
    original: str | None = None
    suggested: str = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=500)
    matched_job_keywords: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(min_length=1)


class OptimizationDraftResponse(DraftModel):
    suggestions: list[OptimizationSuggestionDraft] = Field(default_factory=list)


def _with_skill_deficit_confirmations(
    resume: ResumeSchema,
    job: JobAnalysisSchema,
    match: MatchAnalysisSchema,
    suggestions: list[OptimizationSuggestion],
) -> list[OptimizationSuggestion]:
    result = list(suggestions)
    used_skills = {
        normalize_skill(item.suggested)
        for item in result
        if item.section == "skills"
    }
    tool_terms = {
        normalize_skill(value)
        for value in [*job.tools, *job.cloud_and_devops]
        if normalize_skill(value)
    }
    missing: list[str] = []
    seen: set[str] = set()
    for value in [*match.missing_required_skills, *match.missing_preferred_skills]:
        normalized = normalize_skill(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            missing.append(value)

    confirmations_added = 0
    for skill in missing:
        normalized = normalize_skill(skill)
        if (
            len(result) >= MAX_OPTIMIZATION_SUGGESTIONS
            or confirmations_added >= MAX_SKILL_CONFIRMATIONS
        ):
            break
        if normalized in used_skills:
            continue
        suggestion_type: SuggestionType = (
            "confirm_tool_skill" if normalized in tool_terms else "confirm_technical_skill"
        )
        suggestion_type = _normalized_skill_suggestion_type(suggestion_type, skill)
        placeholder = OptimizationSuggestion(
            id=str(uuid4()),
            section="skills",
            item_index=None,
            bullet_index=None,
            type=suggestion_type,
            original="placeholder",
            suggested=skill,
            reason=(
                f"The job asks for {skill}, but it was not found in your uploaded resume. "
                "Accept only if you genuinely have this skill; otherwise reject it."
            ),
            matched_job_keywords=[skill],
            evidence=[CONFIRMATION_EVIDENCE],
            status="pending",
        )
        suggestion = placeholder.model_copy(
            update={"original": get_target_text(resume, placeholder)}
        )
        validate_suggestion(resume, suggestion)
        result.append(suggestion)
        used_skills.add(normalized)
        confirmations_added += 1
    return result


def _messages(
    resume: ResumeSchema,
    job: JobAnalysisSchema,
    match: MatchAnalysisSchema,
) -> list[dict[str, str]]:
    schema_json = json.dumps(OptimizationDraftResponse.model_json_schema(), ensure_ascii=False)
    resume_json = json.dumps(
        resume.model_dump(exclude={"personal_info"}), ensure_ascii=False
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": build_optimizer_prompt(
                resume_json=resume_json,
                job_json=json.dumps(job.model_dump(), ensure_ascii=False),
                match_json=json.dumps(match.model_dump(), ensure_ascii=False),
                schema_json=schema_json,
                max_suggestions=MAX_OPTIMIZATION_SUGGESTIONS,
            ),
        },
    ]


def generate_resume_suggestions(
    resume: ResumeSchema,
    job: JobAnalysisSchema,
    match: MatchAnalysisSchema,
) -> list[OptimizationSuggestion]:
    messages = _messages(resume, job, match)
    client = get_mistral_client()
    safe: list[OptimizationSuggestion] = []
    targets: set[tuple[str, int | None, int | None, str]] = set()

    for attempt in range(2):
        try:
            response = client.chat.complete(
                model=settings.mistral_model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2,
            )
        except Exception as exc:
            logger.warning("Mistral resume optimization request failed: %s", type(exc).__name__)
            raise MistralServiceError("Mistral request failed.") from exc

        try:
            draft_response = OptimizationDraftResponse.model_validate_json(
                _message_content(response)
            )
        except (ValidationError, MistralResponseError):
            if attempt == 1:
                raise MistralResponseError(
                    "Mistral returned invalid optimization suggestions."
                )
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Return valid JSON only matching the required suggestion schema. "
                        "Do not include markdown or explanatory text."
                    ),
                }
            )
            continue

        for draft in draft_response.suggestions[:MAX_OPTIMIZATION_SUGGESTIONS]:
            suggestion_id = str(uuid4())
            try:
                suggestion_type = _normalized_skill_suggestion_type(
                    draft.type,
                    draft.suggested,
                )
                placeholder = OptimizationSuggestion(
                    id=suggestion_id,
                    section=draft.section,
                    item_index=draft.item_index,
                    bullet_index=draft.bullet_index,
                    type=suggestion_type,
                    original=draft.original or "placeholder",
                    suggested=draft.suggested,
                    reason=draft.reason,
                    matched_job_keywords=draft.matched_job_keywords,
                    evidence=draft.evidence,
                    status="pending",
                )
                target = get_target_text(resume, placeholder)
                suggestion = placeholder.model_copy(update={"original": target})
                target_key = suggestion_target_key(suggestion)
                if target_key in targets:
                    continue
                validate_suggestion(resume, suggestion)
                targets.add(target_key)
                safe.append(suggestion)
            except (ValidationError, UnsafeSuggestionError):
                logger.info("Unsafe or invalid optimization suggestion was dropped.")

        if len(safe) >= MIN_USEFUL_SUGGESTIONS or attempt == 1:
            return _with_skill_deficit_confirmations(resume, job, match, safe)

        used_targets = ", ".join(
            f"{kind}:{item_index}:{bullet_index}:{skill}"
            for kind, item_index, bullet_index, skill in sorted(
                targets,
                key=lambda value: (
                    value[0],
                    -1 if value[1] is None else value[1],
                    -1 if value[2] is None else value[2],
                    value[3],
                ),
            )
        ) or "none"
        messages.append(
            {
                "role": "user",
                "content": (
                    "The previous response produced too few distinct suggestions that "
                    "passed factual validation. Add conservative edits for other targets. "
                    f"Do not repeat these already-used targets: {used_targets}. Reuse exact "
                    "facts and numbers from the target and evidence. Prioritize truthfully "
                    "supported missing ATS terminology, then clarity and relevance. Do not "
                    "add any unsupported skill, responsibility, metric, or impact claim."
                ),
            }
        )

    raise MistralResponseError("Mistral returned no optimization response.")
