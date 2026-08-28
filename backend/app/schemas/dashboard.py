from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DashboardModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HistoryItem(DashboardModel):
    job_id: str
    resume_id: str
    optimization_id: str | None = None
    company: str
    role: str
    resume_filename: str
    before_score: int | None = None
    after_score: int | None = None
    status: str
    has_pdf: bool
    created_at: datetime


class HistoryResponse(DashboardModel):
    items: list[HistoryItem]
