from pydantic import BaseModel


class ChatQuery(BaseModel):
    query: str
    session_id: str | None = None
