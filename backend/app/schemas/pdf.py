from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.optimization import validate_uuid_string
from app.schemas.resume import ResumeSchema


class PDFModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PDFGenerationResponse(PDFModel):
    optimization_id: str
    resume_id: str
    job_id: str
    status: Literal["generated"]
    preview_url: str
    download_url: str
    expires_in: int
    filename: str


class PDFAccessResponse(PDFModel):
    optimization_id: str
    resume_id: str
    job_id: str
    status: Literal["access_refreshed"]
    preview_url: str
    download_url: str
    expires_in: int
    filename: str
