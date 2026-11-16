from datetime import date
from typing import Literal

from pydantic import AnyHttpUrl, Field

from app.schemas.trip_context import StrictModel


class PlaceSource(StrictModel):
    title: str
    url: AnyHttpUrl
    accessed_on: date


class PlaceRecord(StrictModel):
    id: str
    name: str
    category: Literal["cave", "waterfall", "village", "river_activity"]
    area: str
    district: str
    summary: str
    setting: Literal["indoor", "outdoor", "mixed"]
    tags: list[str] = Field(default_factory=list)
    source: PlaceSource
