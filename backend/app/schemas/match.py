from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.job import JobAnalysisSchema
from app.schemas.resume import ResumeSchema


class MatchModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CategoryScore(MatchModel):
    score: float = Field(ge=0)
    max_score: float = Field(gt=0)
    applicable: bool

    @model_validator(mode="after")
    def score_does_not_exceed_maximum(self) -> "CategoryScore":
        if self.score > self.max_score:
            raise ValueError("category score cannot exceed max_score")
        return self


class MatchBreakdown(MatchModel):
    skills: CategoryScore
    experience: CategoryScore
    projects: CategoryScore
    keywords: CategoryScore
    education: CategoryScore
    completeness: CategoryScore


class MatchAnalysisSchema(MatchModel):
    overall_score: int = Field(ge=0, le=100)
    breakdown: MatchBreakdown
    matched_skills: list[str] = Field(default_factory=list)
    missing_required_skills: list[str] = Field(default_factory=list)
    missing_preferred_skills: list[str] = Field(default_factory=list)
    matched_keywords: list[str] = Field(default_factory=list)
    missing_keywords: list[str] = Field(default_factory=list)
    relevant_experience: list[str] = Field(default_factory=list)
    relevant_projects: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class MatchRequest(MatchModel):
    resume_id: str
    job_id: str
    resume: ResumeSchema
    job: JobAnalysisSchema

    @field_validator("resume_id", "job_id", mode="before")
    @classmethod
    def validate_identifier(cls, value: object) -> str:
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


class MatchResponse(MatchModel):
    resume_id: str
    job_id: str
    status: Literal["matched"]
    match: MatchAnalysisSchema
