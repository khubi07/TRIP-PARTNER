from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.place import PlaceRecord


class SearchFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    area: str | None = None
    category: Literal["cave", "waterfall", "village", "river_activity"] | None = None
    setting: Literal["indoor", "outdoor", "mixed"] | None = None


class PlaceSearchResult(BaseModel):
    record: PlaceRecord
    bm25_score: float
    query_coverage: float = Field(ge=0.0, le=1.0)
    matched_terms: list[str]


class PlaceSearchResponse(BaseModel):
    query: str
    applied_filters: SearchFilters
    results: list[PlaceSearchResult]
    needs_refinement: bool
    fallback_message: str | None = None
