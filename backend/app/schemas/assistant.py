from pydantic import Field

from app.schemas.trip_context import StrictModel


class ChatRequest(StrictModel):
    message: str = Field(min_length=1, max_length=1000)


class Citation(StrictModel):
    source_id: str
    source_type: str
    title: str
    url: str


class ChatResponse(StrictModel):
    intent: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    needs_refinement: bool = False
    fallback_message: str | None = None
