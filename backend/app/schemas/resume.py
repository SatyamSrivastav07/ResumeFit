from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


TECHNICAL_SKILL_KEYS = {
    "c", "cpp", "csharp", "css", "css3", "html", "html5", "java",
    "javascript", "typescript", "python", "go", "golang", "rust", "php",
    "kotlin", "swift", "sql", "nosql", "react", "reactjs", "nextjs",
    "nodejs", "expressjs", "fastapi", "django", "flask", "springboot",
    "angular", "vuejs", "tailwindcss", "bootstrap", "restapi", "graphql",
    "mongodb", "mysql", "postgresql", "sqlite", "redis", "dynamodb",
    "datastructures", "algorithms", "dsa", "oop", "microservices", "rag",
}
TOOL_PLATFORM_KEYS = {
    "git", "github", "gitlab", "bitbucket", "vscode", "visualstudiocode",
    "visualstudio", "intellijidea", "pycharm", "eclipse", "postman", "swagger",
    "docker", "kubernetes", "jenkins", "githubactions", "cicd", "terraform",
    "ansible", "jira", "linux", "npm", "yarn", "maven", "gradle", "vite",
    "webpack", "aws", "azure", "gcp", "googlecloudplatform", "firebase",
    "vercel", "netlify", "render", "railway", "heroku", "mongodbcompass",
}


def _skill_key(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def classify_skill_category(value: str) -> Literal["technical", "tools"] | None:
    key = _skill_key(value)
    if key in TECHNICAL_SKILL_KEYS:
        return "technical"
    if key in TOOL_PLATFORM_KEYS:
        return "tools"
    return None


def _deduplicate_skills(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = _skill_key(value)
        if key and key not in seen:
            seen.add(key)
            result.append(value)
    return result


class ResumeModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PersonalInfo(ResumeModel):
    name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=50)
    location: str | None = Field(default=None, max_length=250)
    linkedin: str | None = Field(default=None, max_length=500)
    github: str | None = Field(default=None, max_length=500)
    portfolio: str | None = Field(default=None, max_length=500)


class Skills(ResumeModel):
    technical: list[str] = Field(default_factory=list, max_length=200)
    tools: list[str] = Field(default_factory=list, max_length=200)
    soft: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def separate_technical_skills_and_tools(self) -> "Skills":
        technical = [
            value for value in self.technical
            if classify_skill_category(value) != "tools"
        ]
        tools = [
            value for value in self.tools
            if classify_skill_category(value) != "technical"
        ]
        technical.extend(
            value for value in self.tools
            if classify_skill_category(value) == "technical"
        )
        tools.extend(
            value for value in self.technical
            if classify_skill_category(value) == "tools"
        )
        self.technical = _deduplicate_skills(technical)
        self.tools = _deduplicate_skills(tools)
        return self


class ExperienceItem(ResumeModel):
    company: str = Field(max_length=200)
    role: str = Field(max_length=200)
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: list[str] = Field(default_factory=list, max_length=100)


class ProjectItem(ResumeModel):
    name: str = Field(max_length=300)
    description: list[str] = Field(default_factory=list, max_length=100)
    technologies: list[str] = Field(default_factory=list, max_length=100)
    # `link` remains for previously parsed resumes. New parses keep repository
    # and deployed-application URLs separately so both survive optimization.
    link: str | None = Field(default=None, max_length=500)
    github_link: str | None = Field(
        default=None,
        max_length=500,
        description="Existing GitHub repository URL explicitly shown for this project.",
    )
    live_link: str | None = Field(
        default=None,
        max_length=500,
        description="Existing deployed application or live demo URL explicitly shown for this project.",
    )


class EducationItem(ResumeModel):
    institution: str = Field(max_length=300)
    degree: str | None = None
    field: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    score: str | None = None


class ResumeSchema(ResumeModel):
    personal_info: PersonalInfo = Field(default_factory=PersonalInfo)
    summary: str | None = Field(default=None, max_length=4_000)
    skills: Skills = Field(default_factory=Skills)
    experience: list[ExperienceItem] = Field(default_factory=list, max_length=50)
    projects: list[ProjectItem] = Field(default_factory=list, max_length=50)
    education: list[EducationItem] = Field(default_factory=list, max_length=30)
    certifications: list[str] = Field(default_factory=list, max_length=100)
    achievements: list[str] = Field(default_factory=list, max_length=100)
    languages: list[str] = Field(default_factory=list, max_length=50)


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
