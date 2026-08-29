import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

ExperienceLevel = Literal[
    "Internship",
    "Entry Level",
    "Junior",
    "Mid Level",
    "Senior",
    "Lead",
    "Manager",
    "Director",
    "Unspecified",
]
EmploymentType = Literal[
    "Full-time",
    "Part-time",
    "Internship",
    "Contract",
    "Temporary",
    "Unspecified",
]


class JobModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class JobAnalysisRequest(JobModel):
    resume_id: str
    company: str = Field(min_length=1, max_length=150)
    role: str = Field(min_length=1, max_length=150)
    job_description: str = Field(min_length=100, max_length=30_000)

    @field_validator("resume_id", mode="before")
    @classmethod
    def validate_resume_id(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("resume_id must be a valid UUID")
        cleaned = value.strip().lower()
        try:
            parsed = UUID(cleaned)
        except ValueError as exc:
            raise ValueError("resume_id must be a valid UUID") from exc
        if str(parsed) != cleaned:
            raise ValueError("resume_id must be a canonical UUID")
        return cleaned

    @field_validator("job_description", mode="before")
    @classmethod
    def normalize_job_description(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
        return re.sub(r"\n[\t ]*\n(?:[\t ]*\n)+", "\n\n", normalized)


class JobAnalysisSchema(JobModel):
    company: str = Field(max_length=150)
    role: str = Field(max_length=150)
    experience_level: ExperienceLevel = "Unspecified"
    employment_type: EmploymentType = "Unspecified"
    required_skills: list[str] = Field(default_factory=list, max_length=200)
    preferred_skills: list[str] = Field(default_factory=list, max_length=200)
    programming_languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    cloud_and_devops: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    experience_requirements: list[str] = Field(default_factory=list)
    important_keywords: list[str] = Field(default_factory=list)
    domain_keywords: list[str] = Field(default_factory=list)


class JobAnalysisResponse(BaseModel):
    job_id: str
    resume_id: str
    status: Literal["analyzed"]
    analysis: JobAnalysisSchema


class JobDetailResponse(JobModel):
    job_id: str
    resume_id: str
    company: str
    role: str
    job_description: str
    analysis: JobAnalysisSchema
    match_analysis: dict | None = None
    status: Literal["analyzed", "matched", "optimization_started", "completed"]
    created_at: datetime
    updated_at: datetime


class JobListResponse(JobModel):
    items: list["JobListItem"]


class JobListItem(JobModel):
    job_id: str
    resume_id: str
    company: str
    role: str
    status: Literal["analyzed", "matched", "optimization_started", "completed"]
    created_at: datetime
    updated_at: datetime
