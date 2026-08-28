from pydantic import BaseModel


class CurrentUser(BaseModel):
    uid: str
    email: str | None = None
