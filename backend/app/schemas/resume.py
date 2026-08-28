from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ResumeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PersonalInfo(ResumeModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None


class Skills(ResumeModel):
    technical: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    soft: list[str] = Field(default_factory=list)


class ExperienceItem(ResumeModel):
    company: str
    role: str
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: list[str] = Field(default_factory=list)


class ProjectItem(ResumeModel):
    name: str
    description: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    link: str | None = None


class EducationItem(ResumeModel):
    institution: str
    degree: str | None = None
    field: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    score: str | None = None


class ResumeSchema(ResumeModel):
    personal_info: PersonalInfo = Field(default_factory=PersonalInfo)
    summary: str | None = None
    skills: Skills = Field(default_factory=Skills)
    experience: list[ExperienceItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)


class ResumeUploadResponse(BaseModel):
    resume_id: str
    filename: str
    size: int
    content_type: Literal["application/pdf"]
    status: Literal["uploaded"]


class ResumeParseResponse(BaseModel):
    resume_id: str
    status: Literal["parsed"]
    resume: ResumeSchema


class ResumeDetailResponse(ResumeModel):
    resume_id: str
    filename: str
    status: Literal["uploaded", "parsed", "parse_failed"]
    parsed_resume: ResumeSchema | None = None
    created_at: datetime
    updated_at: datetime


class ResumeListItem(ResumeModel):
    resume_id: str
    filename: str
    status: Literal["uploaded", "parsed", "parse_failed"]
    created_at: datetime
    updated_at: datetime


class ResumeListResponse(ResumeModel):
    items: list[ResumeListItem]


class ResumePDFAccessResponse(ResumeModel):
    resume_id: str
    status: Literal["access_refreshed"]
    preview_url: str
    download_url: str
    expires_in: int
    filename: str
