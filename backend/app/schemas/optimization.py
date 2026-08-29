from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.job import JobAnalysisSchema
from app.schemas.match import MatchAnalysisSchema
from app.schemas.resume import ResumeSchema

SuggestionType = Literal[
    "rewrite_summary",
    "rewrite_experience_bullet",
    "rewrite_project_bullet",
    "add_technical_skill",
    "add_tool_skill",
    "confirm_technical_skill",
    "confirm_tool_skill",
]
SuggestionStatus = Literal["pending", "accepted", "rejected", "edited"]


def validate_uuid_string(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("identifier must be a valid UUID")
    cleaned = value.strip().lower()
    try:
        parsed = UUID(cleaned)
    except ValueError as exc:
        raise ValueError("identifier must be a valid UUID") from exc
    if str(parsed) != cleaned:
        raise ValueError("identifier must be a canonical UUID")
    return cleaned


class OptimizationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OptimizationSuggestion(OptimizationModel):
    id: str
    section: Literal["summary", "experience", "projects", "skills"]
    item_index: int | None = Field(default=None, ge=0)
    bullet_index: int | None = Field(default=None, ge=0)
    type: SuggestionType
    original: str = Field(min_length=1)
    suggested: str = Field(min_length=1, max_length=2_000)
    reason: str = Field(min_length=1, max_length=500)
    matched_job_keywords: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(min_length=1, max_length=20)
    status: SuggestionStatus = "pending"

    @field_validator("id", mode="before")
    @classmethod
    def validate_id(cls, value: object) -> str:
        return validate_uuid_string(value)

    @model_validator(mode="after")
    def validate_target_shape(self) -> "OptimizationSuggestion":
        expected = {
            "rewrite_summary": "summary",
            "rewrite_experience_bullet": "experience",
            "rewrite_project_bullet": "projects",
            "add_technical_skill": "skills",
            "add_tool_skill": "skills",
            "confirm_technical_skill": "skills",
            "confirm_tool_skill": "skills",
        }[self.type]
        if self.section != expected:
            raise ValueError("suggestion type does not match its section")
        if self.type in {
            "rewrite_summary",
            "add_technical_skill",
            "add_tool_skill",
            "confirm_technical_skill",
            "confirm_tool_skill",
        }:
            if self.item_index is not None or self.bullet_index is not None:
                raise ValueError("summary and skill suggestions cannot include item indexes")
        elif self.item_index is None or self.bullet_index is None:
            raise ValueError("bullet rewrites require item_index and bullet_index")
        return self


class OptimizationRequest(OptimizationModel):
    resume_id: str
    job_id: str
    resume: ResumeSchema
    job: JobAnalysisSchema
    match: MatchAnalysisSchema

    @field_validator("resume_id", "job_id", mode="before")
    @classmethod
    def validate_workflow_id(cls, value: object) -> str:
        return validate_uuid_string(value)


class OptimizationResponse(OptimizationModel):
    optimization_id: str
    resume_id: str
    job_id: str
    status: Literal["suggestions_generated"]
    suggestions: list[OptimizationSuggestion]


class PersistentOptimizationRequest(OptimizationModel):
    job_id: str

    @field_validator("job_id", mode="before")
    @classmethod
    def validate_job_id(cls, value: object) -> str:
        return validate_uuid_string(value)


class SuggestionDecision(OptimizationModel):
    id: str
    status: Literal["accepted", "rejected", "edited"]
    edited_text: str | None = Field(default=None, min_length=1, max_length=2_000)

    @field_validator("id", mode="before")
    @classmethod
    def validate_id(cls, value: object) -> str:
        return validate_uuid_string(value)

    @model_validator(mode="after")
    def validate_decision(self) -> "SuggestionDecision":
        if self.status == "edited" and not self.edited_text:
            raise ValueError("edited_text is required for edited suggestions")
        if self.status != "edited" and self.edited_text is not None:
            raise ValueError("edited_text is only allowed for edited suggestions")
        return self


class ApplyPersistentOptimizationRequest(OptimizationModel):
    suggestions: list[SuggestionDecision] = Field(max_length=100)


class GeneratedPDFMetadata(OptimizationModel):
    filename: str
    generated_at: datetime


class OptimizationDetailResponse(OptimizationModel):
    optimization_id: str
    resume_id: str
    job_id: str
    suggestions: list[OptimizationSuggestion]
    optimized_resume: ResumeSchema | None = None
    before_match: MatchAnalysisSchema | None = None
    after_match: MatchAnalysisSchema | None = None
    generated_pdf: GeneratedPDFMetadata | None = None
    status: Literal["suggestions_generated", "applied", "generated"]
    created_at: datetime
    updated_at: datetime


class ApplyOptimizationRequest(OptimizationModel):
    resume_id: str
    job_id: str
    optimization_id: str
    resume: ResumeSchema
    job: JobAnalysisSchema
    suggestions: list[OptimizationSuggestion]

    @field_validator("resume_id", "job_id", "optimization_id", mode="before")
    @classmethod
    def validate_workflow_id(cls, value: object) -> str:
        return validate_uuid_string(value)


class ScoreComparison(OptimizationModel):
    before: int = Field(ge=0, le=100)
    after: int = Field(ge=0, le=100)
    change: int = Field(ge=-100, le=100)


class ApplyOptimizationResponse(OptimizationModel):
    optimization_id: str
    status: Literal["applied"]
    optimized_resume: ResumeSchema
    score_comparison: ScoreComparison
    match: MatchAnalysisSchema
