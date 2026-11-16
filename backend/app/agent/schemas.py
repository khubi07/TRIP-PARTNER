from typing import Literal

from pydantic import ConfigDict, Field

from app.schemas.trip_context import StrictModel


class RouteDecision(StrictModel):
    """LLM classification result used to select a graph path and search inputs."""

    intent: Literal["recommendation", "itinerary", "weather", "clarification"]
    retrieval_query: str = Field(default="", max_length=300)
    area: str | None = Field(default=None, max_length=100)
    category: Literal["cave", "waterfall", "village", "river_activity"] | None = None
    setting: Literal["indoor", "outdoor", "mixed"] | None = None
    clarification_question: str = Field(default="", max_length=300)


class AnswerDraft(StrictModel):
    """Response text plus database-owned IDs for validated source references."""

    message: str = Field(min_length=1, max_length=2000)
    cited_place_ids: list[str] = Field(default_factory=list)
